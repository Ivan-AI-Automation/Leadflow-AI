from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

from app.schemas.common import LeadCategory, LeadStatus, PaginationMeta


class LeadBase(BaseModel):
    first_name: str | None = Field(default=None, max_length=100, description="Lead first name.")
    last_name: str | None = Field(default=None, max_length=100, description="Lead last name.")
    company_name: str | None = Field(default=None, max_length=255, description="Company name.")
    job_title: str | None = Field(default=None, max_length=255, description="Lead job title.")
    email: EmailStr | None = Field(default=None, description="Lead email address.")
    phone: str | None = Field(default=None, max_length=50, description="Lead phone number.")
    website: HttpUrl | None = Field(default=None, description="Company or lead website.")
    industry: str | None = Field(default=None, max_length=150, description="Lead industry.")
    source: str | None = Field(default=None, max_length=150, description="Where the lead came from.")
    location: str | None = Field(default=None, max_length=255, description="Lead location.")
    deal_value: Decimal | None = Field(default=None, ge=0, description="Estimated deal value.")
    budget_range: str | None = Field(default=None, max_length=100, description="Budget range label.")
    interest_level: str | None = Field(default=None, max_length=100, description="Observed interest level.")
    timeline: str | None = Field(default=None, max_length=100, description="Expected buying timeline.")
    notes: str | None = Field(default=None, description="Internal notes about the lead.")


class LeadCreateRequest(LeadBase):
    import_id: int | None = Field(default=None, description="Optional import this lead belongs to.")


class LeadUpdateRequest(LeadBase):
    status: LeadStatus | None = Field(default=None, description="Current lead pipeline status.")
    category: LeadCategory | None = Field(default=None, description="Current lead priority category.")
    priority_score: int | None = Field(default=None, ge=0, le=100, description="Follow-up Priority Score.")


class LeadStatusUpdateRequest(BaseModel):
    status: LeadStatus = Field(description="New lead pipeline status.")


class LeadResponse(LeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Unique lead identifier.")
    user_id: int = Field(description="Identifier of the user who owns the lead.")
    import_id: int | None = Field(default=None, description="Import identifier, when uploaded in a batch.")
    status: LeadStatus = Field(description="Current lead pipeline status.")
    category: LeadCategory = Field(description="Current lead priority category.")
    priority_score: int = Field(ge=0, le=100, description="Follow-up Priority Score.")
    missing_fields_json: list[str] = Field(description="Contact or business fields missing from the lead.")
    created_at: datetime = Field(description="Date and time when the lead was created.")
    updated_at: datetime = Field(description="Date and time when the lead was last updated.")


class LeadListResponse(BaseModel):
    items: list[LeadResponse] = Field(description="Leads returned for the current page.")
    meta: PaginationMeta = Field(description="Pagination metadata.")
