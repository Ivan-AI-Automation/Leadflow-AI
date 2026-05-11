from __future__ import annotations

from typing import Literal, TypedDict

import pandas as pd

from app.services.lead_cleaning_service import LeadCleaningService

LeadDatasetType = Literal["b2b_service", "real_estate", "recruitment", "generic"]


class MissingContactReport(TypedDict):
    missing_email_count: int
    missing_phone_count: int
    missing_all_contact_count: int
    rows_missing_email: list[int]
    rows_missing_phone: list[int]
    rows_missing_all_contact: list[int]
    readable_summary: str


class ImportQualityReport(TypedDict):
    row_count: int
    column_count: int
    dataset_type: LeadDatasetType
    missing_email_count: int
    missing_phone_count: int
    missing_company_count: int
    duplicate_lead_count: int
    empty_row_count: int
    critical_missing_fields: dict[str, int]
    quality_score: int
    readable_summary: str


class LeadValidationService:
    @staticmethod
    def detect_missing_contact_data(dataframe: pd.DataFrame) -> MissingContactReport:
        missing_email_rows = LeadValidationService._missing_rows_for_column(dataframe, "email")
        missing_phone_rows = LeadValidationService._missing_rows_for_column(dataframe, "phone")
        missing_all_contact_rows = sorted(set(missing_email_rows) & set(missing_phone_rows))

        return {
            "missing_email_count": len(missing_email_rows),
            "missing_phone_count": len(missing_phone_rows),
            "missing_all_contact_count": len(missing_all_contact_rows),
            "rows_missing_email": missing_email_rows,
            "rows_missing_phone": missing_phone_rows,
            "rows_missing_all_contact": missing_all_contact_rows,
            "readable_summary": LeadValidationService._contact_summary(
                len(missing_email_rows),
                len(missing_phone_rows),
                len(missing_all_contact_rows),
            ),
        }

    @staticmethod
    def detect_missing_required_fields(
        dataframe: pd.DataFrame,
        dataset_type: LeadDatasetType | None = None,
    ) -> dict[str, int]:
        inferred_type = dataset_type or LeadValidationService.infer_lead_dataset_type(dataframe)
        required_fields = LeadValidationService._required_fields_for_dataset(inferred_type)
        missing_fields: dict[str, int] = {}

        for field in required_fields:
            missing_count = len(LeadValidationService._missing_rows_for_column(dataframe, field))
            if missing_count:
                missing_fields[field] = missing_count

        return missing_fields

    @staticmethod
    def infer_lead_dataset_type(dataframe: pd.DataFrame) -> LeadDatasetType:
        columns = set(dataframe.columns)

        if {"hiring_need", "role_type", "urgency"}.issubset(columns):
            return "recruitment"

        if {"property_type", "budget_range", "timeline"}.issubset(columns) and "company_name" not in columns:
            return "real_estate"

        if {"company_name", "job_title", "deal_value", "industry"}.issubset(columns):
            return "b2b_service"

        return "generic"

    @staticmethod
    def build_import_quality_report(dataframe: pd.DataFrame) -> ImportQualityReport:
        cleaned = LeadCleaningService.normalize_text_fields(dataframe)
        cleaned = LeadCleaningService.normalize_email(cleaned)
        cleaned = LeadCleaningService.normalize_phone(cleaned)
        cleaned_without_empty_rows = LeadCleaningService.remove_empty_rows(cleaned)

        row_count = len(cleaned_without_empty_rows)
        column_count = len(cleaned_without_empty_rows.columns)
        empty_row_count = len(cleaned) - row_count

        missing_contact_data = LeadValidationService.detect_missing_contact_data(cleaned_without_empty_rows)
        dataset_type = LeadValidationService.infer_lead_dataset_type(cleaned_without_empty_rows)
        critical_missing_fields = LeadValidationService.detect_missing_required_fields(
            cleaned_without_empty_rows,
            dataset_type,
        )
        duplicates = LeadCleaningService.detect_duplicate_leads(cleaned_without_empty_rows)
        duplicate_lead_count = len(duplicates)
        missing_company_count = LeadValidationService._missing_company_count(cleaned_without_empty_rows)

        quality_score = LeadValidationService._calculate_quality_score(
            row_count=row_count,
            missing_email_count=int(missing_contact_data["missing_email_count"]),
            missing_phone_count=int(missing_contact_data["missing_phone_count"]),
            missing_company_count=missing_company_count,
            duplicate_lead_count=duplicate_lead_count,
            empty_row_count=empty_row_count,
        )

        return {
            "row_count": row_count,
            "column_count": column_count,
            "dataset_type": dataset_type,
            "missing_email_count": missing_contact_data["missing_email_count"],
            "missing_phone_count": missing_contact_data["missing_phone_count"],
            "missing_company_count": missing_company_count,
            "duplicate_lead_count": duplicate_lead_count,
            "empty_row_count": empty_row_count,
            "critical_missing_fields": critical_missing_fields,
            "quality_score": quality_score,
            "readable_summary": LeadValidationService._quality_summary(
                row_count=row_count,
                dataset_type=dataset_type,
                quality_score=quality_score,
                missing_email_count=int(missing_contact_data["missing_email_count"]),
                missing_phone_count=int(missing_contact_data["missing_phone_count"]),
                missing_company_count=missing_company_count,
                duplicate_lead_count=duplicate_lead_count,
                empty_row_count=empty_row_count,
            ),
        }

    @staticmethod
    def _missing_rows_for_column(dataframe: pd.DataFrame, column: str) -> list[int]:
        if column not in dataframe.columns:
            return list(range(len(dataframe)))

        missing_mask = dataframe[column].map(LeadCleaningService._is_missing_value)
        return [int(index) for index in dataframe.index[missing_mask].tolist()]

    @staticmethod
    def _missing_company_count(dataframe: pd.DataFrame) -> int:
        if "company_name" not in dataframe.columns:
            return 0
        return len(LeadValidationService._missing_rows_for_column(dataframe, "company_name"))

    @staticmethod
    def _required_fields_for_dataset(dataset_type: LeadDatasetType) -> list[str]:
        required_fields_by_type: dict[LeadDatasetType, list[str]] = {
            "b2b_service": ["first_name", "last_name", "company_name"],
            "real_estate": ["first_name", "last_name", "location", "property_type"],
            "recruitment": ["first_name", "last_name", "company_name", "hiring_need"],
            "generic": ["first_name", "last_name"],
        }
        return required_fields_by_type[dataset_type]

    @staticmethod
    def _calculate_quality_score(
        *,
        row_count: int,
        missing_email_count: int,
        missing_phone_count: int,
        missing_company_count: int,
        duplicate_lead_count: int,
        empty_row_count: int,
    ) -> int:
        if row_count <= 0:
            return 0

        score = 100.0
        score -= LeadValidationService._ratio_penalty(missing_email_count, row_count, weight=25)
        score -= LeadValidationService._ratio_penalty(missing_phone_count, row_count, weight=15)
        score -= LeadValidationService._ratio_penalty(missing_company_count, row_count, weight=15)
        score -= LeadValidationService._ratio_penalty(duplicate_lead_count, row_count, weight=20)
        score -= min(empty_row_count * 5, 15)

        return max(0, min(100, round(score)))

    @staticmethod
    def _ratio_penalty(issue_count: int, row_count: int, *, weight: int) -> float:
        if row_count <= 0:
            return float(weight)
        return min(issue_count / row_count, 1) * weight

    @staticmethod
    def _contact_summary(
        missing_email_count: int,
        missing_phone_count: int,
        missing_all_contact_count: int,
    ) -> str:
        if missing_email_count == 0 and missing_phone_count == 0:
            return "All leads include both email and phone contact details."

        return (
            f"{missing_email_count} leads are missing an email address, "
            f"{missing_phone_count} leads are missing a phone number, and "
            f"{missing_all_contact_count} leads are missing both contact methods."
        )

    @staticmethod
    def _quality_summary(
        *,
        row_count: int,
        dataset_type: LeadDatasetType,
        quality_score: int,
        missing_email_count: int,
        missing_phone_count: int,
        missing_company_count: int,
        duplicate_lead_count: int,
        empty_row_count: int,
    ) -> str:
        if row_count == 0:
            return "No usable lead rows were found after removing empty rows."

        issues: list[str] = []
        if missing_email_count:
            issues.append(f"{missing_email_count} missing email values")
        if missing_phone_count:
            issues.append(f"{missing_phone_count} missing phone values")
        if missing_company_count:
            issues.append(f"{missing_company_count} missing company names")
        if duplicate_lead_count:
            issues.append(f"{duplicate_lead_count} duplicate-looking lead rows")
        if empty_row_count:
            issues.append(f"{empty_row_count} empty rows removed")

        if issues:
            issue_text = ", ".join(issues)
            return (
                f"This looks like a {dataset_type} dataset with {row_count} usable rows. "
                f"The quality score is {quality_score}/100 because of {issue_text}."
            )

        return (
            f"This looks like a {dataset_type} dataset with {row_count} usable rows. "
            f"The quality score is {quality_score}/100 and no major import issues were found."
        )
