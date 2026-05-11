from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class LeadActivityResponse(ORMBaseModel):
    id: int = Field(description="Unique activity identifier.")
    lead_id: int = Field(description="Identifier of the related lead.")
    user_id: int = Field(description="Identifier of the user who owns the activity.")
    activity_type: str = Field(description="Type of activity recorded.")
    description: str = Field(description="Human-readable activity description.")
    created_at: datetime = Field(description="Date and time when the activity was recorded.")
