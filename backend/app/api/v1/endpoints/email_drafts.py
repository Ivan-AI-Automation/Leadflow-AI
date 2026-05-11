from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import EmailDraftStatus, EmailTone, LeadCategory, MessageResponse
from app.schemas.email_draft import (
    EmailDraftBulkCreateRequest,
    EmailDraftBulkCreateResponse,
    EmailDraftGenerateRequest,
    EmailDraftListResponse,
    EmailDraftRewriteRequest,
    EmailDraftResponse,
    EmailDraftUpdateRequest,
)
from app.services.email_draft_service import EmailDraftService

router = APIRouter(tags=["email drafts"])


@router.post("/leads/{lead_id}/email-draft", response_model=EmailDraftResponse, status_code=201)
def generate_email_draft_for_lead(
    lead_id: int,
    request: EmailDraftGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EmailDraftResponse:
    draft = EmailDraftService().generate_for_lead(
        db,
        current_user=current_user,
        lead_id=lead_id,
        request=request,
    )
    return EmailDraftResponse.model_validate(draft)


@router.post("/email-drafts/bulk", response_model=EmailDraftBulkCreateResponse, status_code=201)
def generate_email_drafts_in_bulk(
    request: EmailDraftBulkCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EmailDraftBulkCreateResponse:
    return EmailDraftService().generate_bulk(
        db,
        current_user=current_user,
        request=request,
    )


@router.get("/email-drafts", response_model=EmailDraftListResponse)
def list_email_drafts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    status: EmailDraftStatus | None = None,
    tone: EmailTone | None = None,
    lead_category: LeadCategory | None = None,
    search: str | None = Query(default=None, description="Search text across draft and lead fields."),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="created_at", pattern="^created_at$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> EmailDraftListResponse:
    filters = {
        "status": status.value if status else None,
        "tone": tone.value if tone else None,
        "lead_category": lead_category.value if lead_category else None,
        "search": search,
    }
    return EmailDraftService.list_drafts(
        db,
        current_user=current_user,
        filters=filters,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/email-drafts/{draft_id}", response_model=EmailDraftResponse)
def get_email_draft(
    draft_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EmailDraftResponse:
    draft = EmailDraftService.get_draft(db, current_user=current_user, draft_id=draft_id)
    return EmailDraftResponse.model_validate(draft)


@router.patch("/email-drafts/{draft_id}", response_model=EmailDraftResponse)
def update_email_draft(
    draft_id: int,
    request: EmailDraftUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EmailDraftResponse:
    draft = EmailDraftService.update_draft(
        db,
        current_user=current_user,
        draft_id=draft_id,
        request=request,
    )
    return EmailDraftResponse.model_validate(draft)


@router.delete("/email-drafts/{draft_id}", response_model=MessageResponse)
def delete_email_draft(
    draft_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    EmailDraftService.archive_draft(db, current_user=current_user, draft_id=draft_id)
    return MessageResponse(message="Email draft archived successfully.")


@router.patch("/email-drafts/{draft_id}/approve", response_model=EmailDraftResponse)
def approve_email_draft(
    draft_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EmailDraftResponse:
    draft = EmailDraftService.approve_draft(db, current_user=current_user, draft_id=draft_id)
    return EmailDraftResponse.model_validate(draft)


@router.post("/email-drafts/{draft_id}/rewrite", response_model=EmailDraftResponse)
def rewrite_email_draft(
    draft_id: int,
    request: EmailDraftRewriteRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EmailDraftResponse:
    draft = EmailDraftService().rewrite_draft(
        db,
        current_user=current_user,
        draft_id=draft_id,
        request=request,
    )
    return EmailDraftResponse.model_validate(draft)
