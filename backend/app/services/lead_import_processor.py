from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.lead_import import LeadImport
from app.models.user import User
from app.repositories.import_repository import get_lead_import_for_user, update_lead_import_status
from app.repositories.lead_repository import create_leads, delete_leads_for_import
from app.schemas.lead_import import LeadImportProcessResponse
from app.services.data_loader import DataLoader
from app.services.lead_cleaning_service import LeadCleaningService
from app.services.lead_validation_service import LeadDatasetType, LeadValidationService

logger = get_logger(__name__)

LEAD_MODEL_FIELDS = {
    "first_name",
    "last_name",
    "company_name",
    "job_title",
    "email",
    "phone",
    "website",
    "industry",
    "source",
    "location",
    "deal_value",
    "budget_range",
    "interest_level",
    "timeline",
    "notes",
}

COLUMN_ALIASES = {
    "company": "company_name",
    "organisation": "company_name",
    "organization": "company_name",
    "title": "job_title",
    "role": "job_title",
    "email_address": "email",
    "mobile": "phone",
    "mobile_phone": "phone",
    "telephone": "phone",
    "lead_source": "source",
    "city": "location",
    "region": "location",
    "estimated_value": "deal_value",
    "estimated_deal_value": "deal_value",
}


class LeadImportProcessor:
    @staticmethod
    def process_import(
        db: Session,
        *,
        current_user: User,
        import_id: int,
    ) -> LeadImportProcessResponse:
        lead_import = LeadImportProcessor._get_owned_import(
            db,
            current_user=current_user,
            import_id=import_id,
        )
        file_path = LeadImportProcessor._stored_file_path(lead_import)

        dataframe = DataLoader.load_by_file_path(file_path)
        DataLoader.validate_dataframe_not_empty(dataframe)

        normalized_dataframe = DataLoader.normalize_column_names(dataframe)
        normalized_dataframe = LeadImportProcessor._apply_column_aliases(normalized_dataframe)
        cleaned_dataframe = LeadImportProcessor._clean_dataframe(normalized_dataframe)
        usable_dataframe = LeadCleaningService.remove_empty_rows(cleaned_dataframe)

        quality_report = LeadValidationService.build_import_quality_report(cleaned_dataframe)
        dataset_type = LeadValidationService.infer_lead_dataset_type(usable_dataframe)

        delete_leads_for_import(db, import_id=lead_import.id, user_id=current_user.id)

        lead_rows = LeadImportProcessor._build_lead_rows(
            usable_dataframe,
            current_user=current_user,
            lead_import=lead_import,
            dataset_type=dataset_type,
        )
        created_leads = create_leads(db, lead_rows) if lead_rows else []
        updated_import = update_lead_import_status(db, lead_import, status="processed")

        logger.info(
            "User %s processed import %s and created %s leads",
            current_user.id,
            lead_import.id,
            len(created_leads),
        )

        readable_summary = LeadImportProcessor._processing_summary(
            created_count=len(created_leads),
            quality_summary=str(quality_report["readable_summary"]),
        )

        return LeadImportProcessResponse(
            import_id=updated_import.id,
            status=updated_import.status,
            dataset_type=dataset_type,
            created_leads_count=len(created_leads),
            skipped_rows_count=int(quality_report["empty_row_count"]),
            row_count=int(quality_report["row_count"]),
            missing_email_count=int(quality_report["missing_email_count"]),
            missing_phone_count=int(quality_report["missing_phone_count"]),
            missing_company_count=int(quality_report["missing_company_count"]),
            duplicate_lead_count=int(quality_report["duplicate_lead_count"]),
            critical_missing_fields=dict(quality_report["critical_missing_fields"]),
            quality_score=int(quality_report["quality_score"]),
            readable_summary=readable_summary,
        )

    @staticmethod
    def _get_owned_import(db: Session, *, current_user: User, import_id: int) -> LeadImport:
        lead_import = get_lead_import_for_user(db, import_id=import_id, user_id=current_user.id)
        if lead_import is None:
            raise NotFoundError("The requested import was not found.")
        return lead_import

    @staticmethod
    def _stored_file_path(lead_import: LeadImport) -> Path:
        settings = get_settings()
        file_path = settings.upload_dir / lead_import.stored_filename
        if not file_path.exists():
            raise NotFoundError("The uploaded import file could not be found on disk.")
        return file_path

    @staticmethod
    def _apply_column_aliases(dataframe: pd.DataFrame) -> pd.DataFrame:
        renamed_columns = {
            column: COLUMN_ALIASES[column]
            for column in dataframe.columns
            if column in COLUMN_ALIASES and COLUMN_ALIASES[column] not in dataframe.columns
        }
        if not renamed_columns:
            return dataframe.copy()
        return dataframe.rename(columns=renamed_columns)

    @staticmethod
    def _clean_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
        cleaned = LeadCleaningService.normalize_text_fields(dataframe)
        cleaned = LeadCleaningService.normalize_email(cleaned)
        cleaned = LeadCleaningService.normalize_phone(cleaned)
        cleaned = LeadCleaningService.normalize_budget_range(cleaned)
        cleaned = LeadCleaningService.normalize_timeline(cleaned)
        return cleaned

    @staticmethod
    def _build_lead_rows(
        dataframe: pd.DataFrame,
        *,
        current_user: User,
        lead_import: LeadImport,
        dataset_type: LeadDatasetType,
    ) -> list[dict[str, Any]]:
        lead_rows: list[dict[str, Any]] = []

        for _, row in dataframe.iterrows():
            lead_data = LeadImportProcessor._map_row_to_lead_data(
                row,
                current_user=current_user,
                lead_import=lead_import,
                dataset_type=dataset_type,
            )
            lead_rows.append(lead_data)

        return lead_rows

    @staticmethod
    def _map_row_to_lead_data(
        row: pd.Series,
        *,
        current_user: User,
        lead_import: LeadImport,
        dataset_type: LeadDatasetType,
    ) -> dict[str, Any]:
        lead_data: dict[str, Any] = {
            "user_id": current_user.id,
            "import_id": lead_import.id,
            "status": "New",
            "category": "Unscored",
            "priority_score": 0,
        }

        for field in LEAD_MODEL_FIELDS:
            lead_data[field] = LeadImportProcessor._row_value(row, field)

        lead_data["deal_value"] = LeadImportProcessor._parse_deal_value(lead_data.get("deal_value"))
        lead_data["industry"] = LeadImportProcessor._infer_industry(
            existing_industry=lead_data.get("industry"),
            dataset_type=dataset_type,
        )
        lead_data["interest_level"] = LeadImportProcessor._infer_interest_level(
            row=row,
            existing_interest_level=lead_data.get("interest_level"),
            dataset_type=dataset_type,
        )
        lead_data["notes"] = LeadImportProcessor._build_notes(
            row=row,
            existing_notes=lead_data.get("notes"),
            dataset_type=dataset_type,
        )
        lead_data["missing_fields_json"] = LeadImportProcessor._missing_fields_for_row(
            row,
            dataset_type=dataset_type,
        )

        return lead_data

    @staticmethod
    def _row_value(row: pd.Series, column: str) -> Any | None:
        if column not in row:
            return None
        value = row[column]
        if LeadCleaningService._is_missing_value(value):
            return None
        return value.item() if hasattr(value, "item") else value

    @staticmethod
    def _parse_deal_value(value: object) -> Decimal | None:
        if value is None or LeadCleaningService._is_missing_value(value):
            return None

        try:
            normalized_value = str(value).replace(",", "").replace("$", "").replace(chr(163), "").strip()
            return Decimal(normalized_value)
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _infer_industry(*, existing_industry: object | None, dataset_type: LeadDatasetType) -> object | None:
        if existing_industry:
            return existing_industry
        if dataset_type == "real_estate":
            return "Real Estate"
        if dataset_type == "recruitment":
            return "Recruitment"
        return None

    @staticmethod
    def _infer_interest_level(
        *,
        row: pd.Series,
        existing_interest_level: object | None,
        dataset_type: LeadDatasetType,
    ) -> object | None:
        if existing_interest_level:
            return existing_interest_level
        if dataset_type == "recruitment":
            return LeadImportProcessor._row_value(row, "urgency")
        return None

    @staticmethod
    def _build_notes(
        *,
        row: pd.Series,
        existing_notes: object | None,
        dataset_type: LeadDatasetType,
    ) -> str | None:
        notes_parts: list[str] = []

        if existing_notes:
            notes_parts.append(str(existing_notes))

        if dataset_type == "real_estate":
            LeadImportProcessor._append_context_note(notes_parts, "Property type", row, "property_type")

        if dataset_type == "recruitment":
            LeadImportProcessor._append_context_note(notes_parts, "Hiring need", row, "hiring_need")
            LeadImportProcessor._append_context_note(notes_parts, "Role type", row, "role_type")
            LeadImportProcessor._append_context_note(notes_parts, "Urgency", row, "urgency")

        return " ".join(notes_parts) if notes_parts else None

    @staticmethod
    def _append_context_note(notes_parts: list[str], label: str, row: pd.Series, column: str) -> None:
        value = LeadImportProcessor._row_value(row, column)
        if value:
            notes_parts.append(f"{label}: {value}.")

    @staticmethod
    def _missing_fields_for_row(row: pd.Series, *, dataset_type: LeadDatasetType) -> list[str]:
        fields = ["email", "phone"]
        fields.extend(LeadValidationService._required_fields_for_dataset(dataset_type))

        missing_fields: list[str] = []
        for field in fields:
            if field in missing_fields:
                continue
            value = LeadImportProcessor._row_value(row, field)
            if value is None:
                missing_fields.append(field)

        return missing_fields

    @staticmethod
    def _processing_summary(*, created_count: int, quality_summary: str) -> str:
        return f"Created {created_count} lead records. {quality_summary}"
