from typing import Literal

from pydantic import BaseModel, Field


class DashboardSummaryResponse(BaseModel):
    total_leads: int = Field(ge=0, description="Total number of leads.")
    new_leads: int = Field(ge=0, description="Number of leads with New status.")
    contacted_leads: int = Field(ge=0, description="Number of leads with Contacted status.")
    follow_up_leads: int = Field(ge=0, description="Number of leads with Follow-up status.")
    closed_leads: int = Field(ge=0, description="Number of leads with Closed status.")
    lost_leads: int = Field(ge=0, description="Number of leads with Lost status.")
    hot_leads: int = Field(ge=0, description="Number of leads categorized as Hot.")
    warm_leads: int = Field(ge=0, description="Number of leads categorized as Warm.")
    nurture_leads: int = Field(ge=0, description="Number of leads categorized as Nurture.")
    low_priority_leads: int = Field(ge=0, description="Number of leads categorized as Low Priority.")
    missing_email_count: int = Field(ge=0, description="Number of leads missing an email address.")
    missing_phone_count: int = Field(ge=0, description="Number of leads missing a phone number.")
    average_priority_score: float = Field(ge=0, le=100, description="Average Follow-up Priority Score.")
    drafts_created: int = Field(ge=0, description="Number of email drafts created.")
    drafts_approved: int = Field(ge=0, description="Number of approved email drafts.")


class BarChartData(BaseModel):
    id: str = Field(description="Stable chart identifier.")
    title: str = Field(description="Human-readable chart title.")
    type: Literal["bar"] = Field(description="Chart type.")
    x: list[str] = Field(description="X-axis labels.")
    y: list[int] = Field(description="Y-axis values.")


class PieChartData(BaseModel):
    id: str = Field(description="Stable chart identifier.")
    title: str = Field(description="Human-readable chart title.")
    type: Literal["pie"] = Field(description="Chart type.")
    labels: list[str] = Field(description="Slice labels.")
    values: list[int] = Field(description="Slice values.")


class DashboardChartsResponse(BaseModel):
    charts: list[BarChartData | PieChartData] = Field(description="Chart-ready dashboard data.")
