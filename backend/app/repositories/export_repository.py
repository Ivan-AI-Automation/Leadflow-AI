from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.email_draft import EmailDraft
from app.models.exported_email_batch import ExportedEmailBatch
from app.models.lead import Lead


def list_exportable_email_drafts(
    db: Session,
    *,
    user_id: int,
    statuses: list[str],
    draft_ids: list[int] | None = None,
) -> list[EmailDraft]:
    conditions: list[Any] = [
        EmailDraft.user_id == user_id,
        EmailDraft.status.in_(statuses),
        Lead.email.is_not(None),
        Lead.email != "",
    ]
    if draft_ids is not None:
        conditions.append(EmailDraft.id.in_(draft_ids))

    statement = (
        select(EmailDraft)
        .join(Lead, EmailDraft.lead_id == Lead.id)
        .where(*conditions)
        .order_by(EmailDraft.created_at.asc(), EmailDraft.id.asc())
    )
    return list(db.scalars(statement).all())


def create_export_batch(
    db: Session,
    *,
    user_id: int,
    export_format: str,
    file_path: str,
    lead_count: int,
    commit: bool = True,
) -> ExportedEmailBatch:
    export_batch = ExportedEmailBatch(
        user_id=user_id,
        format=export_format,
        file_path=file_path,
        lead_count=lead_count,
    )
    db.add(export_batch)

    if commit:
        db.commit()
        db.refresh(export_batch)

    return export_batch


def get_export_batch_for_user(
    db: Session,
    *,
    export_id: int,
    user_id: int,
) -> ExportedEmailBatch | None:
    statement = select(ExportedEmailBatch).where(
        ExportedEmailBatch.id == export_id,
        ExportedEmailBatch.user_id == user_id,
    )
    return db.scalar(statement)


def list_export_batches_for_user(
    db: Session,
    *,
    user_id: int,
    limit: int,
    offset: int,
) -> tuple[list[ExportedEmailBatch], int]:
    total_statement = select(func.count()).select_from(ExportedEmailBatch).where(ExportedEmailBatch.user_id == user_id)
    total = int(db.scalar(total_statement) or 0)

    statement = (
        select(ExportedEmailBatch)
        .where(ExportedEmailBatch.user_id == user_id)
        .order_by(ExportedEmailBatch.created_at.desc(), ExportedEmailBatch.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement).all()), total
