from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.lead_activity import LeadActivity


def create_lead_activity(
    db: Session,
    *,
    lead_id: int,
    user_id: int,
    activity_type: str,
    description: str,
    commit: bool = True,
) -> LeadActivity:
    activity = LeadActivity(
        lead_id=lead_id,
        user_id=user_id,
        activity_type=activity_type,
        description=description,
    )
    db.add(activity)

    if commit:
        db.commit()
        db.refresh(activity)

    return activity


def list_lead_activities_for_user(
    db: Session,
    *,
    lead_id: int,
    user_id: int,
    limit: int = 50,
) -> list[LeadActivity]:
    statement = (
        select(LeadActivity)
        .where(
            LeadActivity.lead_id == lead_id,
            LeadActivity.user_id == user_id,
        )
        .order_by(LeadActivity.created_at.desc(), LeadActivity.id.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())
