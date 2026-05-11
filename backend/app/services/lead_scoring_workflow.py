from collections import Counter

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.lead import Lead
from app.models.lead_score import LeadScore
from app.models.user import User
from app.repositories.import_repository import get_lead_import_for_user
from app.repositories.lead_repository import get_lead_for_user, list_leads_for_import, list_leads_for_user
from app.repositories.lead_score_repository import get_lead_score_for_lead, upsert_lead_score
from app.schemas.lead_score import LeadScoreSummaryResponse
from app.services.lead_scoring_service import LeadScoringService

logger = get_logger(__name__)


class LeadScoringWorkflow:
    @staticmethod
    def score_single_lead(db: Session, *, current_user: User, lead_id: int) -> LeadScore:
        lead = LeadScoringWorkflow._get_owned_lead(db, current_user=current_user, lead_id=lead_id)
        lead_score = LeadScoringWorkflow._score_and_save(db, lead)

        logger.info(
            "User %s scored lead %s with score %s and category %s",
            current_user.id,
            lead.id,
            lead_score.score,
            lead_score.category,
        )

        return lead_score

    @staticmethod
    def get_single_lead_score(db: Session, *, current_user: User, lead_id: int) -> LeadScore:
        lead = LeadScoringWorkflow._get_owned_lead(db, current_user=current_user, lead_id=lead_id)
        lead_score = get_lead_score_for_lead(db, lead_id=lead.id)
        if lead_score is None:
            raise NotFoundError("This lead has not been scored yet.")
        return lead_score

    @staticmethod
    def score_import_leads(db: Session, *, current_user: User, import_id: int) -> LeadScoreSummaryResponse:
        lead_import = get_lead_import_for_user(db, import_id=import_id, user_id=current_user.id)
        if lead_import is None:
            raise NotFoundError("The requested import was not found.")

        leads = list_leads_for_import(db, import_id=import_id, user_id=current_user.id)
        summary = LeadScoringWorkflow._score_many(db, leads)

        logger.info(
            "User %s scored %s leads from import %s",
            current_user.id,
            summary.total_scored,
            import_id,
        )

        return summary

    @staticmethod
    def score_all_user_leads(db: Session, *, current_user: User) -> LeadScoreSummaryResponse:
        leads = list_leads_for_user(db, user_id=current_user.id)
        summary = LeadScoringWorkflow._score_many(db, leads)

        logger.info(
            "User %s scored all current leads. Total scored: %s",
            current_user.id,
            summary.total_scored,
        )

        return summary

    @staticmethod
    def _get_owned_lead(db: Session, *, current_user: User, lead_id: int) -> Lead:
        lead = get_lead_for_user(db, lead_id=lead_id, user_id=current_user.id)
        if lead is None:
            raise NotFoundError("The requested lead was not found.")
        return lead

    @staticmethod
    def _score_many(db: Session, leads: list[Lead]) -> LeadScoreSummaryResponse:
        categories: Counter[str] = Counter()

        for lead in leads:
            lead_score = LeadScoringWorkflow._score_and_save(db, lead)
            categories[lead_score.category] += 1

        return LeadScoreSummaryResponse(
            total_scored=len(leads),
            hot_count=categories["Hot"],
            warm_count=categories["Warm"],
            nurture_count=categories["Nurture"],
            low_priority_count=categories["Low Priority"],
        )

    @staticmethod
    def _score_and_save(db: Session, lead: Lead) -> LeadScore:
        score_result = LeadScoringService.score_lead(lead)
        return upsert_lead_score(
            db,
            lead=lead,
            score=int(score_result["score"]),
            category=str(score_result["category"]),
            score_breakdown_json=dict(score_result["breakdown"]),
            recommendation=str(score_result["recommendation"]),
        )
