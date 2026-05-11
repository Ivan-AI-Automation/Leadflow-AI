from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.lead_activity_repository import list_lead_activities_for_user
from app.schemas.common import LeadCategory, LeadStatus, MessageResponse
from app.schemas.lead_activity import LeadActivityResponse
from app.schemas.lead import (
    LeadCreateRequest,
    LeadListResponse,
    LeadResponse,
    LeadStatusUpdateRequest,
    LeadUpdateRequest,
)
from app.services.lead_service import LeadService

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=LeadListResponse)
def list_leads(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    status: LeadStatus | None = None,
    category: LeadCategory | None = None,
    source: str | None = None,
    industry: str | None = None,
    location: str | None = None,
    min_score: int | None = Query(default=None, ge=0, le=100),
    max_score: int | None = Query(default=None, ge=0, le=100),
    search: str | None = Query(
        default=None, description="Search text across lead name, company, email, phone, and notes."
    ),
    missing_email: bool | None = None,
    missing_phone: bool | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="created_at", pattern="^(priority_score|created_at)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> LeadListResponse:
    filters = {
        "status": status.value if status else None,
        "category": category.value if category else None,
        "source": source,
        "industry": industry,
        "location": location,
        "min_score": min_score,
        "max_score": max_score,
        "search": search,
        "missing_email": missing_email,
        "missing_phone": missing_phone,
    }
    return LeadService.list_leads(
        db,
        current_user=current_user,
        filters=filters,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post("", response_model=LeadResponse, status_code=201)
def create_lead(
    request: LeadCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> LeadResponse:
    lead = LeadService.create_lead_for_user(db, current_user=current_user, request=request)
    return LeadResponse.model_validate(lead)


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> LeadResponse:
    lead = LeadService.get_lead(db, current_user=current_user, lead_id=lead_id)
    return LeadResponse.model_validate(lead)


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    request: LeadUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> LeadResponse:
    lead = LeadService.update_lead_for_user(db, current_user=current_user, lead_id=lead_id, request=request)
    return LeadResponse.model_validate(lead)


@router.delete("/{lead_id}", response_model=MessageResponse)
def delete_lead(
    lead_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    LeadService.delete_lead_for_user(db, current_user=current_user, lead_id=lead_id)
    return MessageResponse(message="Lead deleted successfully.")


@router.patch("/{lead_id}/status", response_model=LeadResponse)
def update_lead_status(
    lead_id: int,
    request: LeadStatusUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> LeadResponse:
    lead = LeadService.update_lead_status(db, current_user=current_user, lead_id=lead_id, request=request)
    return LeadResponse.model_validate(lead)


@router.get("/{lead_id}/activities", response_model=list[LeadActivityResponse])
def list_lead_activities(
    lead_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
) -> list[LeadActivityResponse]:
    LeadService.get_lead(db, current_user=current_user, lead_id=lead_id)
    activities = list_lead_activities_for_user(
        db,
        lead_id=lead_id,
        user_id=current_user.id,
        limit=limit,
    )
    return [LeadActivityResponse.model_validate(activity) for activity in activities]
