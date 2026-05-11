from typing import Any, cast

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.models.lead import Lead


def create_lead(db: Session, lead_data: dict[str, Any]) -> Lead:
    lead = Lead(**lead_data)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def create_leads(db: Session, lead_rows: list[dict[str, object]]) -> list[Lead]:
    leads = [Lead(**row) for row in lead_rows]
    db.add_all(leads)
    db.commit()

    for lead in leads:
        db.refresh(lead)

    return leads


def get_lead_for_user(db: Session, *, lead_id: int, user_id: int) -> Lead | None:
    statement = select(Lead).where(
        Lead.id == lead_id,
        Lead.user_id == user_id,
    )
    return db.scalar(statement)


def list_leads_for_user(db: Session, *, user_id: int) -> list[Lead]:
    statement = select(Lead).where(Lead.user_id == user_id).order_by(Lead.id)
    return list(db.scalars(statement).all())


def list_filtered_leads_for_user(
    db: Session,
    *,
    user_id: int,
    filters: dict[str, Any],
    limit: int,
    offset: int,
    sort_by: str,
    sort_order: str,
) -> tuple[list[Lead], int]:
    conditions = _lead_filter_conditions(user_id=user_id, filters=filters)
    total_statement = select(func.count()).select_from(Lead).where(*conditions)
    total = int(db.scalar(total_statement) or 0)

    sort_column = Lead.priority_score if sort_by == "priority_score" else Lead.created_at
    ordered_column = sort_column.asc() if sort_order == "asc" else sort_column.desc()

    statement = select(Lead).where(*conditions).order_by(ordered_column, Lead.id.desc()).limit(limit).offset(offset)
    leads = list(db.scalars(statement).all())
    return leads, total


def list_leads_for_import(db: Session, *, import_id: int, user_id: int) -> list[Lead]:
    statement = (
        select(Lead)
        .where(
            Lead.import_id == import_id,
            Lead.user_id == user_id,
        )
        .order_by(Lead.id)
    )
    return list(db.scalars(statement).all())


def update_lead(db: Session, lead: Lead, lead_data: dict[str, Any]) -> Lead:
    for field_name, value in lead_data.items():
        setattr(lead, field_name, value)

    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def delete_lead(db: Session, lead: Lead) -> None:
    db.delete(lead)
    db.commit()


def delete_leads_for_import(db: Session, *, import_id: int, user_id: int) -> int:
    statement = delete(Lead).where(
        Lead.import_id == import_id,
        Lead.user_id == user_id,
    )
    result = db.execute(statement)
    db.commit()
    rowcount = cast(Any, result).rowcount
    return int(rowcount or 0)


def _lead_filter_conditions(*, user_id: int, filters: dict[str, Any]) -> list[Any]:
    conditions: list[Any] = [Lead.user_id == user_id]

    if filters.get("status"):
        conditions.append(Lead.status == filters["status"])
    if filters.get("category"):
        conditions.append(Lead.category == filters["category"])
    if filters.get("source"):
        conditions.append(Lead.source.ilike(f"%{filters['source']}%"))
    if filters.get("industry"):
        conditions.append(Lead.industry.ilike(f"%{filters['industry']}%"))
    if filters.get("location"):
        conditions.append(Lead.location.ilike(f"%{filters['location']}%"))
    if filters.get("min_score") is not None:
        conditions.append(Lead.priority_score >= filters["min_score"])
    if filters.get("max_score") is not None:
        conditions.append(Lead.priority_score <= filters["max_score"])
    if filters.get("missing_email") is True:
        conditions.append(or_(Lead.email.is_(None), Lead.email == ""))
    if filters.get("missing_email") is False:
        conditions.append(Lead.email.is_not(None))
        conditions.append(Lead.email != "")
    if filters.get("missing_phone") is True:
        conditions.append(or_(Lead.phone.is_(None), Lead.phone == ""))
    if filters.get("missing_phone") is False:
        conditions.append(Lead.phone.is_not(None))
        conditions.append(Lead.phone != "")

    search_query = filters.get("search")
    if search_query:
        search_pattern = f"%{search_query}%"
        conditions.append(
            or_(
                Lead.first_name.ilike(search_pattern),
                Lead.last_name.ilike(search_pattern),
                Lead.company_name.ilike(search_pattern),
                Lead.email.ilike(search_pattern),
                Lead.phone.ilike(search_pattern),
                Lead.notes.ilike(search_pattern),
            )
        )

    return conditions
