from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.email_draft import EmailDraft
from app.models.lead import Lead


def create_email_draft(db: Session, draft_data: dict[str, Any], *, commit: bool = True) -> EmailDraft:
    draft = EmailDraft(**draft_data)
    db.add(draft)

    if commit:
        db.commit()
        db.refresh(draft)

    return draft


def get_email_draft_for_user(db: Session, *, draft_id: int, user_id: int) -> EmailDraft | None:
    statement = select(EmailDraft).where(
        EmailDraft.id == draft_id,
        EmailDraft.user_id == user_id,
    )
    return db.scalar(statement)


def get_latest_email_draft_for_lead(
    db: Session,
    *,
    lead_id: int,
    user_id: int,
) -> EmailDraft | None:
    statement = (
        select(EmailDraft)
        .where(
            EmailDraft.lead_id == lead_id,
            EmailDraft.user_id == user_id,
            EmailDraft.status != "Archived",
        )
        .order_by(EmailDraft.created_at.desc(), EmailDraft.id.desc())
        .limit(1)
    )
    return db.scalar(statement)


def list_email_drafts_for_user(
    db: Session,
    *,
    user_id: int,
    filters: dict[str, Any],
    limit: int,
    offset: int,
    sort_order: str,
) -> tuple[list[EmailDraft], int]:
    conditions = _email_draft_filter_conditions(user_id=user_id, filters=filters)

    total_statement = (
        select(func.count()).select_from(EmailDraft).join(Lead, EmailDraft.lead_id == Lead.id).where(*conditions)
    )
    total = int(db.scalar(total_statement) or 0)

    ordered_created_at = EmailDraft.created_at.asc() if sort_order == "asc" else EmailDraft.created_at.desc()
    statement = (
        select(EmailDraft)
        .join(Lead, EmailDraft.lead_id == Lead.id)
        .where(*conditions)
        .order_by(ordered_created_at, EmailDraft.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement).all()), total


def update_email_draft(
    db: Session,
    draft: EmailDraft,
    draft_data: dict[str, Any],
    *,
    commit: bool = True,
) -> EmailDraft:
    for field_name, value in draft_data.items():
        setattr(draft, field_name, value)

    db.add(draft)

    if commit:
        db.commit()
        db.refresh(draft)

    return draft


def _email_draft_filter_conditions(*, user_id: int, filters: dict[str, Any]) -> list[Any]:
    conditions: list[Any] = [EmailDraft.user_id == user_id]

    if filters.get("status"):
        conditions.append(EmailDraft.status == filters["status"])
    if filters.get("tone"):
        conditions.append(EmailDraft.tone == filters["tone"])
    if filters.get("lead_category"):
        conditions.append(Lead.category == filters["lead_category"])

    search_query = filters.get("search")
    if search_query:
        search_pattern = f"%{search_query}%"
        conditions.append(
            or_(
                EmailDraft.subject.ilike(search_pattern),
                EmailDraft.body.ilike(search_pattern),
                Lead.first_name.ilike(search_pattern),
                Lead.last_name.ilike(search_pattern),
                Lead.company_name.ilike(search_pattern),
                Lead.email.ilike(search_pattern),
            )
        )

    return conditions
