from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.lead_score import LeadScoreResponse, LeadScoreSummaryResponse
from app.services.lead_scoring_workflow import LeadScoringWorkflow

router = APIRouter(tags=["scoring"])


@router.post("/leads/score-all", response_model=LeadScoreSummaryResponse)
def score_all_leads(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> LeadScoreSummaryResponse:
    return LeadScoringWorkflow.score_all_user_leads(db, current_user=current_user)


@router.post("/leads/{lead_id}/score", response_model=LeadScoreResponse)
def score_lead(
    lead_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> LeadScoreResponse:
    lead_score = LeadScoringWorkflow.score_single_lead(db, current_user=current_user, lead_id=lead_id)
    return LeadScoreResponse.model_validate(lead_score)


@router.get("/leads/{lead_id}/score", response_model=LeadScoreResponse)
def get_lead_score(
    lead_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> LeadScoreResponse:
    lead_score = LeadScoringWorkflow.get_single_lead_score(db, current_user=current_user, lead_id=lead_id)
    return LeadScoreResponse.model_validate(lead_score)


@router.post("/imports/{import_id}/score", response_model=LeadScoreSummaryResponse)
def score_import_leads(
    import_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> LeadScoreSummaryResponse:
    return LeadScoringWorkflow.score_import_leads(db, current_user=current_user, import_id=import_id)
