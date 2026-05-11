from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import LeadCategory, ORMBaseModel


class LeadScoreResponse(ORMBaseModel):
    id: int = Field(description="Unique lead score identifier.")
    lead_id: int = Field(description="Identifier of the scored lead.")
    score: int = Field(ge=0, le=100, description="Deterministic Follow-up Priority Score.")
    category: LeadCategory = Field(description="Priority category derived from the score.")
    score_breakdown_json: dict[str, Any] = Field(description="Explainable score breakdown.")
    recommendation: str | None = Field(default=None, description="Recommended next action.")
    created_at: datetime = Field(description="Date and time when the score was created.")


class LeadScoreSummaryResponse(ORMBaseModel):
    total_scored: int = Field(ge=0, description="Total number of leads scored.")
    hot_count: int = Field(ge=0, description="Number of scored leads categorized as Hot.")
    warm_count: int = Field(ge=0, description="Number of scored leads categorized as Warm.")
    nurture_count: int = Field(ge=0, description="Number of scored leads categorized as Nurture.")
    low_priority_count: int = Field(ge=0, description="Number of scored leads categorized as Low Priority.")
