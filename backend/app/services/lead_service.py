from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.lead import Lead
from app.models.user import User
from app.repositories.lead_activity_repository import create_lead_activity
from app.repositories.lead_repository import (
    create_lead,
    delete_lead,
    get_lead_for_user,
    list_filtered_leads_for_user,
    update_lead,
)
from app.schemas.common import LeadCategory, LeadStatus, PaginationMeta
from app.schemas.lead import (
    LeadCreateRequest,
    LeadListResponse,
    LeadResponse,
    LeadStatusUpdateRequest,
    LeadUpdateRequest,
)

logger = get_logger(__name__)


class LeadService:
    @staticmethod
    def list_leads(
        db: Session,
        *,
        current_user: User,
        filters: dict[str, Any],
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> LeadListResponse:
        LeadService._validate_pagination(limit=limit, offset=offset)
        LeadService._validate_sorting(sort_by=sort_by, sort_order=sort_order)
        leads, total = list_filtered_leads_for_user(
            db,
            user_id=current_user.id,
            filters=filters,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return LeadListResponse(
            items=[LeadResponse.model_validate(lead) for lead in leads],
            meta=PaginationMeta(total=total, limit=limit, offset=offset),
        )

    @staticmethod
    def create_lead_for_user(db: Session, *, current_user: User, request: LeadCreateRequest) -> Lead:
        lead_data = LeadService._request_data_to_db_values(request.model_dump(exclude_unset=True))
        lead_data["user_id"] = current_user.id
        lead_data.setdefault("status", LeadStatus.NEW.value)
        lead_data.setdefault("category", LeadCategory.UNSCORED.value)
        lead_data.setdefault("priority_score", 0)
        lead_data["missing_fields_json"] = LeadService._missing_fields(lead_data)

        lead = create_lead(db, lead_data)
        logger.info("User %s created lead %s", current_user.id, lead.id)
        return lead

    @staticmethod
    def get_lead(db: Session, *, current_user: User, lead_id: int) -> Lead:
        lead = get_lead_for_user(db, lead_id=lead_id, user_id=current_user.id)
        if lead is None:
            raise NotFoundError("The requested lead was not found.")
        return lead

    @staticmethod
    def update_lead_for_user(
        db: Session,
        *,
        current_user: User,
        lead_id: int,
        request: LeadUpdateRequest,
    ) -> Lead:
        lead = LeadService.get_lead(db, current_user=current_user, lead_id=lead_id)
        lead_data = LeadService._request_data_to_db_values(request.model_dump(exclude_unset=True))

        if not lead_data:
            return lead

        current_values = LeadService._lead_to_dict(lead)
        current_values.update(lead_data)
        lead_data["missing_fields_json"] = LeadService._missing_fields(current_values)

        updated_lead = update_lead(db, lead, lead_data)
        logger.info("User %s updated lead %s", current_user.id, lead.id)
        return updated_lead

    @staticmethod
    def delete_lead_for_user(db: Session, *, current_user: User, lead_id: int) -> None:
        lead = LeadService.get_lead(db, current_user=current_user, lead_id=lead_id)
        delete_lead(db, lead)
        logger.info("User %s deleted lead %s", current_user.id, lead_id)

    @staticmethod
    def update_lead_status(
        db: Session,
        *,
        current_user: User,
        lead_id: int,
        request: LeadStatusUpdateRequest,
    ) -> Lead:
        lead = LeadService.get_lead(db, current_user=current_user, lead_id=lead_id)
        old_status = lead.status
        new_status = request.status.value

        if old_status == new_status:
            return lead

        lead.status = new_status
        create_lead_activity(
            db,
            lead_id=lead.id,
            user_id=current_user.id,
            activity_type="status_changed",
            description=f"Status changed from {old_status} to {new_status}.",
            commit=False,
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)

        logger.info(
            "User %s changed lead %s status from %s to %s",
            current_user.id,
            lead.id,
            old_status,
            new_status,
        )
        return lead

    @staticmethod
    def _request_data_to_db_values(data: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for field_name, value in data.items():
            if isinstance(value, (LeadStatus, LeadCategory)):
                normalized[field_name] = value.value
            elif field_name == "website" and value is not None:
                normalized[field_name] = str(value)
            elif isinstance(value, Decimal):
                normalized[field_name] = value
            else:
                normalized[field_name] = value
        return normalized

    @staticmethod
    def _missing_fields(values: dict[str, Any]) -> list[str]:
        fields_to_check = ["email", "phone", "first_name", "last_name"]
        if LeadService._is_missing(values.get("company_name")) and LeadService._is_missing(values.get("website")):
            fields_to_check.append("company_name")

        missing_fields = [
            field_name for field_name in fields_to_check if LeadService._is_missing(values.get(field_name))
        ]
        return missing_fields

    @staticmethod
    def _lead_to_dict(lead: Lead) -> dict[str, Any]:
        return {
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "company_name": lead.company_name,
            "job_title": lead.job_title,
            "email": lead.email,
            "phone": lead.phone,
            "website": lead.website,
            "industry": lead.industry,
            "source": lead.source,
            "location": lead.location,
            "deal_value": lead.deal_value,
            "budget_range": lead.budget_range,
            "interest_level": lead.interest_level,
            "timeline": lead.timeline,
            "notes": lead.notes,
            "status": lead.status,
            "category": lead.category,
            "priority_score": lead.priority_score,
        }

    @staticmethod
    def _is_missing(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        return False

    @staticmethod
    def _validate_pagination(*, limit: int, offset: int) -> None:
        if limit < 1 or limit > 200:
            raise ValidationError("Limit must be between 1 and 200.")
        if offset < 0:
            raise ValidationError("Offset must be greater than or equal to 0.")

    @staticmethod
    def _validate_sorting(*, sort_by: str, sort_order: str) -> None:
        if sort_by not in {"priority_score", "created_at"}:
            raise ValidationError("sort_by must be either priority_score or created_at.")
        if sort_order not in {"asc", "desc"}:
            raise ValidationError("sort_order must be either asc or desc.")
