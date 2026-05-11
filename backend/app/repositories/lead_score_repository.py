from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.lead_score import LeadScore


def get_lead_score_for_lead(db: Session, *, lead_id: int) -> LeadScore | None:
    statement = select(LeadScore).where(LeadScore.lead_id == lead_id)
    return db.scalar(statement)


def upsert_lead_score(
    db: Session,
    *,
    lead: Lead,
    score: int,
    category: str,
    score_breakdown_json: dict[str, int],
    recommendation: str,
) -> LeadScore:
    lead_score = get_lead_score_for_lead(db, lead_id=lead.id)

    if lead_score is None:
        lead_score = LeadScore(
            lead_id=lead.id,
            score=score,
            category=category,
            score_breakdown_json=score_breakdown_json,
            recommendation=recommendation,
        )
        db.add(lead_score)
    else:
        lead_score.score = score
        lead_score.category = category
        lead_score.score_breakdown_json = score_breakdown_json
        lead_score.recommendation = recommendation

    lead.priority_score = score
    lead.category = category
    db.add(lead)
    db.commit()
    db.refresh(lead)
    db.refresh(lead_score)
    return lead_score
