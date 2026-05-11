from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AIProviderError, ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.email_draft import EmailDraft
from app.models.lead import Lead
from app.models.user import User
from app.repositories.email_draft_repository import (
    create_email_draft,
    get_email_draft_for_user,
    get_latest_email_draft_for_lead,
    list_email_drafts_for_user,
    update_email_draft,
)
from app.repositories.lead_activity_repository import create_lead_activity
from app.repositories.lead_repository import get_lead_for_user
from app.schemas.common import EmailDraftStatus, EmailTone, PaginationMeta
from app.schemas.email_draft import (
    EmailDraftBulkCreateRequest,
    EmailDraftBulkCreateResponse,
    EmailDraftGenerateRequest,
    EmailDraftListResponse,
    EmailDraftResponse,
    EmailDraftRewriteRequest,
    EmailDraftSkippedLead,
    EmailDraftUpdateRequest,
)
from app.services.ai.ai_service import AIService
from app.services.ai.base import sanitize_ai_context

logger = get_logger(__name__)


class EmailDraftService:
    def __init__(self, ai_service: AIService | None = None, *, ai_provider_name: str | None = None) -> None:
        self.ai_service = ai_service or AIService()
        self.ai_provider_name = ai_provider_name or get_settings().ai_provider

    @staticmethod
    def list_drafts(
        db: Session,
        *,
        current_user: User,
        filters: dict[str, Any],
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> EmailDraftListResponse:
        EmailDraftService._validate_pagination(limit=limit, offset=offset)
        EmailDraftService._validate_sorting(sort_by=sort_by, sort_order=sort_order)
        drafts, total = list_email_drafts_for_user(
            db,
            user_id=current_user.id,
            filters=filters,
            limit=limit,
            offset=offset,
            sort_order=sort_order,
        )
        return EmailDraftListResponse(
            items=[EmailDraftResponse.model_validate(draft) for draft in drafts],
            meta=PaginationMeta(total=total, limit=limit, offset=offset),
        )

    @staticmethod
    def get_draft(db: Session, *, current_user: User, draft_id: int) -> EmailDraft:
        draft = get_email_draft_for_user(db, draft_id=draft_id, user_id=current_user.id)
        if draft is None:
            raise NotFoundError("The requested email draft was not found.")
        return draft

    @staticmethod
    def update_draft(
        db: Session,
        *,
        current_user: User,
        draft_id: int,
        request: EmailDraftUpdateRequest,
    ) -> EmailDraft:
        draft = EmailDraftService.get_draft(db, current_user=current_user, draft_id=draft_id)
        EmailDraftService._validate_draft_can_be_changed(draft)

        update_data = EmailDraftService._manual_update_data(request)
        if not update_data:
            return draft

        update_data["status"] = EmailDraftStatus.DRAFT.value
        updated_draft = update_email_draft(db, draft, update_data, commit=False)
        create_lead_activity(
            db,
            lead_id=draft.lead_id,
            user_id=current_user.id,
            activity_type="email_draft_edited",
            description="Email draft edited manually.",
            commit=False,
        )
        db.commit()
        db.refresh(updated_draft)
        logger.info("User %s edited email draft %s", current_user.id, draft.id)
        return updated_draft

    @staticmethod
    def approve_draft(db: Session, *, current_user: User, draft_id: int) -> EmailDraft:
        draft = EmailDraftService.get_draft(db, current_user=current_user, draft_id=draft_id)
        if draft.status == EmailDraftStatus.ARCHIVED.value:
            raise ValidationError("Archived email drafts cannot be approved.")
        if not draft.subject.strip() or not draft.body.strip():
            raise ValidationError("Email draft must have a subject and body before approval.")

        approved_draft = update_email_draft(
            db,
            draft,
            {"status": EmailDraftStatus.APPROVED.value},
            commit=False,
        )
        create_lead_activity(
            db,
            lead_id=draft.lead_id,
            user_id=current_user.id,
            activity_type="email_draft_approved",
            description="Email draft approved.",
            commit=False,
        )
        db.commit()
        db.refresh(approved_draft)
        logger.info("User %s approved email draft %s", current_user.id, draft.id)
        return approved_draft

    @staticmethod
    def archive_draft(db: Session, *, current_user: User, draft_id: int) -> None:
        draft = EmailDraftService.get_draft(db, current_user=current_user, draft_id=draft_id)
        if draft.status == EmailDraftStatus.ARCHIVED.value:
            return

        update_email_draft(
            db,
            draft,
            {"status": EmailDraftStatus.ARCHIVED.value},
            commit=False,
        )
        create_lead_activity(
            db,
            lead_id=draft.lead_id,
            user_id=current_user.id,
            activity_type="email_draft_archived",
            description="Email draft archived.",
            commit=False,
        )
        db.commit()
        logger.info("User %s archived email draft %s", current_user.id, draft.id)

    def rewrite_draft(
        self,
        db: Session,
        *,
        current_user: User,
        draft_id: int,
        request: EmailDraftRewriteRequest,
    ) -> EmailDraft:
        draft = self.get_draft(db, current_user=current_user, draft_id=draft_id)
        self._validate_draft_can_be_changed(draft)

        context = self._build_ai_context(
            draft.lead,
            tone=request.tone,
            business_type=request.business_type,
            sender_company_name=request.sender_company_name,
        )
        context["existing_subject"] = draft.subject
        context["existing_body"] = draft.body

        generated = self.ai_service.rewrite_email(context)
        subject = str(generated.get("subject", "")).strip()
        body = str(generated.get("body", "")).strip()
        if not subject or not body:
            raise AIProviderError("The AI provider returned an incomplete email draft.")

        rewritten_draft = update_email_draft(
            db,
            draft,
            {
                "subject": subject,
                "body": body,
                "tone": request.tone.value,
                "status": EmailDraftStatus.DRAFT.value,
                "ai_provider": self.ai_provider_name,
            },
            commit=False,
        )
        create_lead_activity(
            db,
            lead_id=draft.lead_id,
            user_id=current_user.id,
            activity_type="email_draft_rewritten",
            description=f"Email draft rewritten with {request.tone.value} tone.",
            commit=False,
        )
        db.commit()
        db.refresh(rewritten_draft)
        logger.info("User %s rewrote email draft %s", current_user.id, draft.id)
        return rewritten_draft

    def generate_for_lead(
        self,
        db: Session,
        *,
        current_user: User,
        lead_id: int,
        request: EmailDraftGenerateRequest,
    ) -> EmailDraft:
        lead = get_lead_for_user(db, lead_id=lead_id, user_id=current_user.id)
        if lead is None:
            raise NotFoundError("The requested lead was not found.")

        if not self._has_enough_contact_data(lead):
            raise ValidationError("Cannot generate an email draft because this lead does not have an email address.")

        existing_draft = get_latest_email_draft_for_lead(db, lead_id=lead.id, user_id=current_user.id)
        if existing_draft is not None and not request.overwrite_existing:
            raise ConflictError("This lead already has an email draft. Set overwrite_existing to true to replace it.")

        draft = self._generate_and_save_draft(
            db,
            current_user=current_user,
            lead=lead,
            tone=request.tone,
            business_type=request.business_type,
            sender_company_name=request.sender_company_name,
            existing_draft=existing_draft if request.overwrite_existing else None,
        )
        logger.info("User %s generated email draft %s for lead %s", current_user.id, draft.id, lead.id)
        return draft

    def generate_bulk(
        self,
        db: Session,
        *,
        current_user: User,
        request: EmailDraftBulkCreateRequest,
    ) -> EmailDraftBulkCreateResponse:
        drafts: list[EmailDraftResponse] = []
        skipped: list[EmailDraftSkippedLead] = []
        seen_lead_ids: set[int] = set()

        for lead_id in request.lead_ids:
            if lead_id in seen_lead_ids:
                skipped.append(
                    EmailDraftSkippedLead(
                        lead_id=lead_id,
                        reason="Lead was selected more than once.",
                    )
                )
                continue
            seen_lead_ids.add(lead_id)

            lead = get_lead_for_user(db, lead_id=lead_id, user_id=current_user.id)
            if lead is None:
                skipped.append(
                    EmailDraftSkippedLead(
                        lead_id=lead_id,
                        reason="Lead was not found.",
                    )
                )
                continue

            if not self._has_enough_contact_data(lead):
                skipped.append(
                    EmailDraftSkippedLead(
                        lead_id=lead_id,
                        reason="Lead does not have an email address.",
                    )
                )
                continue

            existing_draft = get_latest_email_draft_for_lead(db, lead_id=lead.id, user_id=current_user.id)
            if existing_draft is not None and not request.overwrite_existing:
                skipped.append(
                    EmailDraftSkippedLead(
                        lead_id=lead_id,
                        reason="Lead already has an email draft.",
                    )
                )
                continue

            draft = self._generate_and_save_draft(
                db,
                current_user=current_user,
                lead=lead,
                tone=request.tone,
                business_type=request.business_type,
                sender_company_name=request.sender_company_name,
                existing_draft=existing_draft if request.overwrite_existing else None,
            )
            drafts.append(EmailDraftResponse.model_validate(draft))

        logger.info(
            "User %s bulk generated %s email drafts and skipped %s leads",
            current_user.id,
            len(drafts),
            len(skipped),
        )
        return EmailDraftBulkCreateResponse(
            created_count=len(drafts),
            skipped_count=len(skipped),
            drafts=drafts,
            skipped=skipped,
        )

    def _generate_and_save_draft(
        self,
        db: Session,
        *,
        current_user: User,
        lead: Lead,
        tone: EmailTone,
        business_type: str | None,
        sender_company_name: str | None,
        existing_draft: EmailDraft | None,
    ) -> EmailDraft:
        context = self._build_ai_context(
            lead,
            tone=tone,
            business_type=business_type,
            sender_company_name=sender_company_name,
        )
        generated = self.ai_service.generate_follow_up_email(context)
        subject = str(generated.get("subject", "")).strip()
        body = str(generated.get("body", "")).strip()
        if not subject or not body:
            raise AIProviderError("The AI provider returned an incomplete email draft.")

        draft_data = {
            "user_id": current_user.id,
            "lead_id": lead.id,
            "subject": subject,
            "body": body,
            "tone": tone.value,
            "status": EmailDraftStatus.DRAFT.value,
            "ai_provider": self.ai_provider_name,
        }

        if existing_draft is None:
            draft = create_email_draft(db, draft_data, commit=False)
            activity_description = "Email draft generated."
        else:
            draft = update_email_draft(db, existing_draft, draft_data, commit=False)
            activity_description = "Email draft replaced."

        create_lead_activity(
            db,
            lead_id=lead.id,
            user_id=current_user.id,
            activity_type="email_draft_generated",
            description=activity_description,
            commit=False,
        )
        db.commit()
        db.refresh(draft)
        return draft

    @staticmethod
    def _build_ai_context(
        lead: Lead,
        *,
        tone: EmailTone,
        business_type: str | None,
        sender_company_name: str | None,
    ) -> dict[str, Any]:
        context = {
            "first_name": lead.first_name,
            "company_name": lead.company_name,
            "job_title": lead.job_title,
            "industry": lead.industry,
            "source": lead.source,
            "interest_level": lead.interest_level,
            "timeline": lead.timeline,
            "notes": lead.notes,
            "lead_category": lead.category,
            "priority_score": lead.priority_score,
            "email_tone": tone.value,
            "business_type": business_type,
            "sender_company_name": sender_company_name,
        }
        return sanitize_ai_context(context)

    @staticmethod
    def _has_enough_contact_data(lead: Lead) -> bool:
        return bool(lead.email and lead.email.strip())

    @staticmethod
    def _manual_update_data(request: EmailDraftUpdateRequest) -> dict[str, Any]:
        update_data: dict[str, Any] = {}
        data = request.model_dump(exclude_unset=True)

        if "subject" in data:
            subject = data["subject"].strip() if data["subject"] is not None else ""
            if not subject:
                raise ValidationError("Email draft subject cannot be empty.")
            update_data["subject"] = subject

        if "body" in data:
            body = data["body"].strip() if data["body"] is not None else ""
            if not body:
                raise ValidationError("Email draft body cannot be empty.")
            update_data["body"] = body

        if data.get("tone") is not None:
            update_data["tone"] = data["tone"].value

        return update_data

    @staticmethod
    def _validate_draft_can_be_changed(draft: EmailDraft) -> None:
        if draft.status == EmailDraftStatus.ARCHIVED.value:
            raise ValidationError("Archived email drafts cannot be changed.")
        if draft.status == EmailDraftStatus.EXPORTED.value:
            raise ValidationError("Exported email drafts cannot be changed.")

    @staticmethod
    def _validate_pagination(*, limit: int, offset: int) -> None:
        if limit < 1 or limit > 200:
            raise ValidationError("Limit must be between 1 and 200.")
        if offset < 0:
            raise ValidationError("Offset must be greater than or equal to 0.")

    @staticmethod
    def _validate_sorting(*, sort_by: str, sort_order: str) -> None:
        if sort_by != "created_at":
            raise ValidationError("sort_by must be created_at.")
        if sort_order not in {"asc", "desc"}:
            raise ValidationError("sort_order must be either asc or desc.")
