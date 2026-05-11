from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import EmailDraftStatus, EmailTone, ORMBaseModel, PaginationMeta


class EmailDraftCreateRequest(BaseModel):
    lead_id: int = Field(description="Identifier of the lead this draft is for.")
    tone: EmailTone = Field(default=EmailTone.PROFESSIONAL, description="Requested email tone.")


class EmailDraftGenerateRequest(BaseModel):
    tone: EmailTone = Field(default=EmailTone.PROFESSIONAL, description="Requested email tone.")
    business_type: str | None = Field(
        default=None,
        max_length=120,
        description="Optional sender business type used to guide the draft.",
    )
    sender_company_name: str | None = Field(
        default=None,
        max_length=120,
        description="Optional company name to use in the sender signature.",
    )
    overwrite_existing: bool = Field(
        default=False,
        description="Whether to replace the latest existing draft for this lead.",
    )


class EmailDraftBulkCreateRequest(BaseModel):
    lead_ids: list[int] = Field(
        min_length=1,
        max_length=200,
        description="Lead identifiers to generate drafts for.",
    )
    tone: EmailTone = Field(default=EmailTone.PROFESSIONAL, description="Requested email tone.")
    business_type: str | None = Field(
        default=None,
        max_length=120,
        description="Optional sender business type used to guide the drafts.",
    )
    sender_company_name: str | None = Field(
        default=None,
        max_length=120,
        description="Optional company name to use in the sender signature.",
    )
    overwrite_existing: bool = Field(
        default=False,
        description="Whether to replace the latest existing draft for each lead.",
    )


class EmailDraftUpdateRequest(BaseModel):
    subject: str | None = Field(default=None, max_length=255, description="Updated email subject.")
    body: str | None = Field(default=None, description="Updated email body.")
    tone: EmailTone | None = Field(default=None, description="Updated email tone.")


class EmailDraftRewriteRequest(BaseModel):
    tone: EmailTone = Field(default=EmailTone.PROFESSIONAL, description="Requested tone for the rewritten draft.")
    business_type: str | None = Field(
        default=None,
        max_length=120,
        description="Optional sender business type used to guide the rewrite.",
    )
    sender_company_name: str | None = Field(
        default=None,
        max_length=120,
        description="Optional company name to use in the sender signature.",
    )


class EmailDraftResponse(ORMBaseModel):
    id: int = Field(description="Unique email draft identifier.")
    user_id: int = Field(description="Identifier of the user who owns the draft.")
    lead_id: int = Field(description="Identifier of the related lead.")
    subject: str = Field(description="Email subject line.")
    body: str = Field(description="Email body.")
    tone: EmailTone = Field(description="Email tone.")
    status: EmailDraftStatus = Field(description="Draft approval and export status.")
    ai_provider: str = Field(description="AI provider used to generate the draft.")
    created_at: datetime = Field(description="Date and time when the draft was created.")
    updated_at: datetime = Field(description="Date and time when the draft was last updated.")


class EmailDraftSkippedLead(BaseModel):
    lead_id: int = Field(description="Identifier of the skipped lead.")
    reason: str = Field(description="Business-readable reason the draft was not generated.")


class EmailDraftBulkCreateResponse(BaseModel):
    created_count: int = Field(ge=0, description="Number of drafts created or replaced.")
    skipped_count: int = Field(ge=0, description="Number of leads skipped.")
    drafts: list[EmailDraftResponse] = Field(description="Drafts created or replaced.")
    skipped: list[EmailDraftSkippedLead] = Field(description="Skipped leads and reasons.")


class EmailDraftListResponse(BaseModel):
    items: list[EmailDraftResponse] = Field(description="Email drafts returned for the current page.")
    meta: PaginationMeta = Field(description="Pagination information.")
