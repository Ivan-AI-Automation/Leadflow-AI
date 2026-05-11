from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LeadStatus(str, Enum):
    NEW = "New"
    CONTACTED = "Contacted"
    FOLLOW_UP = "Follow-up"
    CLOSED = "Closed"
    LOST = "Lost"


class LeadCategory(str, Enum):
    HOT = "Hot"
    WARM = "Warm"
    NURTURE = "Nurture"
    LOW_PRIORITY = "Low Priority"
    UNSCORED = "Unscored"


class EmailDraftStatus(str, Enum):
    DRAFT = "Draft"
    APPROVED = "Approved"
    EXPORTED = "Exported"
    ARCHIVED = "Archived"


class EmailTone(str, Enum):
    PROFESSIONAL = "Professional"
    FRIENDLY = "Friendly"
    DIRECT = "Direct"
    WARM = "Warm"
    SHORT = "Short"

    @classmethod
    def _missing_(cls, value: object) -> "EmailTone | None":
        if not isinstance(value, str):
            return None

        normalized = value.strip().lower()
        aliases = {
            "professional": cls.PROFESSIONAL,
            "friendly": cls.FRIENDLY,
            "direct": cls.DIRECT,
            "warm": cls.WARM,
            "short": cls.SHORT,
            "concise": cls.SHORT,
            "persuasive": cls.DIRECT,
        }
        return aliases.get(normalized)


class APIErrorDetail(BaseModel):
    code: str = Field(description="Machine-readable error code.")
    message: str = Field(description="Clear error message for the user or developer.")
    details: Any | None = Field(default=None, description="Optional structured error details.")


class APIErrorResponse(BaseModel):
    error: APIErrorDetail = Field(description="Error information returned by the API.")


class MessageResponse(BaseModel):
    message: str = Field(description="Human-readable confirmation message.")


class PaginationMeta(BaseModel):
    total: int = Field(ge=0, description="Total number of matching records.")
    limit: int = Field(ge=1, description="Maximum number of records returned.")
    offset: int = Field(ge=0, description="Number of records skipped.")


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
