from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.email_draft import EmailDraft
from app.models.exported_email_batch import ExportedEmailBatch
from app.models.user import User
from app.repositories.email_draft_repository import update_email_draft
from app.repositories.export_repository import (
    create_export_batch,
    get_export_batch_for_user,
    list_export_batches_for_user,
    list_exportable_email_drafts,
)
from app.repositories.lead_activity_repository import create_lead_activity
from app.schemas.common import EmailDraftStatus, PaginationMeta
from app.schemas.export import EmailDraftExportRequest, ExportFormat, ExportListResponse, ExportResponse
from app.services.export.csv_export_service import CSVExportService
from app.services.export.excel_export_service import ExcelExportService

logger = get_logger(__name__)

EXPORT_COLUMNS = [
    "lead_id",
    "first_name",
    "last_name",
    "company_name",
    "email",
    "status",
    "category",
    "priority_score",
    "email_subject",
    "email_body",
    "draft_status",
]


class ExportService:
    @staticmethod
    def export_email_drafts(
        db: Session,
        *,
        current_user: User,
        request: EmailDraftExportRequest,
        export_format: ExportFormat,
    ) -> ExportedEmailBatch:
        statuses = [EmailDraftStatus.APPROVED.value]
        if request.include_draft_status:
            statuses.append(EmailDraftStatus.DRAFT.value)

        draft_ids = list(dict.fromkeys(request.draft_ids or [])) or None
        drafts = list_exportable_email_drafts(
            db,
            user_id=current_user.id,
            statuses=statuses,
            draft_ids=draft_ids,
        )
        if not drafts:
            raise ValidationError(ExportService._empty_export_message(request.include_draft_status))

        rows = [ExportService._draft_to_export_row(draft) for draft in drafts]
        export_path = ExportService._build_export_path(
            user_id=current_user.id,
            export_format=export_format,
        )
        ExportService._write_export_file(rows, export_path, export_format=export_format)

        for draft in drafts:
            original_status = draft.status
            update_email_draft(
                db,
                draft,
                {"status": EmailDraftStatus.EXPORTED.value},
                commit=False,
            )
            create_lead_activity(
                db,
                lead_id=draft.lead_id,
                user_id=current_user.id,
                activity_type="email_draft_exported",
                description=f"Email draft exported from {original_status} status.",
                commit=False,
            )

        export_batch = create_export_batch(
            db,
            user_id=current_user.id,
            export_format=export_format.value,
            file_path=str(export_path),
            lead_count=len(rows),
            commit=False,
        )
        db.commit()
        db.refresh(export_batch)

        logger.info(
            "User %s exported %s email drafts to %s",
            current_user.id,
            len(rows),
            export_format.value,
        )
        return export_batch

    @staticmethod
    def list_exports(
        db: Session,
        *,
        current_user: User,
        limit: int,
        offset: int,
    ) -> ExportListResponse:
        ExportService._validate_pagination(limit=limit, offset=offset)
        exports, total = list_export_batches_for_user(
            db,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
        )
        return ExportListResponse(
            items=[ExportResponse.model_validate(export) for export in exports],
            meta=PaginationMeta(total=total, limit=limit, offset=offset),
        )

    @staticmethod
    def get_export_for_download(
        db: Session,
        *,
        current_user: User,
        export_id: int,
    ) -> ExportedEmailBatch:
        export_batch = get_export_batch_for_user(db, export_id=export_id, user_id=current_user.id)
        if export_batch is None:
            raise NotFoundError("The requested export was not found.")

        file_path = Path(export_batch.file_path)
        if not file_path.exists() or not file_path.is_file():
            raise NotFoundError("The exported file was not found on disk.")

        return export_batch

    @staticmethod
    def _draft_to_export_row(draft: EmailDraft) -> dict[str, object]:
        lead = draft.lead
        return {
            "lead_id": lead.id,
            "first_name": lead.first_name or "",
            "last_name": lead.last_name or "",
            "company_name": lead.company_name or "",
            "email": lead.email or "",
            "status": lead.status,
            "category": lead.category,
            "priority_score": lead.priority_score,
            "email_subject": draft.subject,
            "email_body": draft.body,
            "draft_status": draft.status,
        }

    @staticmethod
    def _build_export_path(*, user_id: int, export_format: ExportFormat) -> Path:
        settings = get_settings()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        extension = "xlsx" if export_format == ExportFormat.XLSX else "csv"
        filename = f"leadflow_email_drafts_user_{user_id}_{timestamp}.{extension}"
        return settings.export_dir / filename

    @staticmethod
    def _write_export_file(
        rows: list[dict[str, object]],
        file_path: Path,
        *,
        export_format: ExportFormat,
    ) -> None:
        ordered_rows = [{column: row.get(column, "") for column in EXPORT_COLUMNS} for row in rows]
        if export_format == ExportFormat.CSV:
            CSVExportService.write_email_drafts(ordered_rows, file_path)
            return
        if export_format == ExportFormat.XLSX:
            ExcelExportService.write_email_drafts(ordered_rows, file_path)
            return
        raise ValidationError("Unsupported export format.")

    @staticmethod
    def _empty_export_message(include_draft_status: bool) -> str:
        if include_draft_status:
            return "No approved or draft email drafts are available to export."
        return "No approved email drafts are available to export."

    @staticmethod
    def _validate_pagination(*, limit: int, offset: int) -> None:
        if limit < 1 or limit > 200:
            raise ValidationError("Limit must be between 1 and 200.")
        if offset < 0:
            raise ValidationError("Offset must be greater than or equal to 0.")
