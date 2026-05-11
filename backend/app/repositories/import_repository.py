from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lead_import import LeadImport


def create_lead_import(
    db: Session,
    *,
    user_id: int,
    original_filename: str,
    stored_filename: str,
    file_type: str,
    rows_count: int,
    columns_count: int,
    columns_json: list[str],
    dtypes_json: dict[str, str],
    status: str = "uploaded",
) -> LeadImport:
    lead_import = LeadImport(
        user_id=user_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_type=file_type,
        rows_count=rows_count,
        columns_count=columns_count,
        columns_json=columns_json,
        dtypes_json=dtypes_json,
        status=status,
    )
    db.add(lead_import)
    db.commit()
    db.refresh(lead_import)
    return lead_import


def list_lead_imports_for_user(db: Session, *, user_id: int) -> list[LeadImport]:
    statement = (
        select(LeadImport)
        .where(LeadImport.user_id == user_id)
        .order_by(LeadImport.created_at.desc(), LeadImport.id.desc())
    )
    return list(db.scalars(statement).all())


def get_lead_import_for_user(db: Session, *, import_id: int, user_id: int) -> LeadImport | None:
    statement = select(LeadImport).where(
        LeadImport.id == import_id,
        LeadImport.user_id == user_id,
    )
    return db.scalar(statement)


def delete_lead_import(db: Session, lead_import: LeadImport) -> None:
    db.delete(lead_import)
    db.commit()


def update_lead_import_status(db: Session, lead_import: LeadImport, *, status: str) -> LeadImport:
    lead_import.status = status
    db.add(lead_import)
    db.commit()
    db.refresh(lead_import)
    return lead_import
