from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.common import ORMBaseModel, PaginationMeta


class ExportFormat(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"


class ExportResponse(ORMBaseModel):
    id: int = Field(description="Unique export batch identifier.")
    user_id: int = Field(description="Identifier of the user who created the export.")
    format: ExportFormat = Field(description="Exported file format.")
    file_path: str = Field(description="Path to the exported file.")
    lead_count: int = Field(ge=0, description="Number of leads included in the export.")
    created_at: datetime = Field(description="Date and time when the export was created.")


class EmailDraftExportRequest(BaseModel):
    draft_ids: list[int] | None = Field(
        default=None,
        max_length=500,
        description="Optional draft identifiers to export. If omitted, all eligible drafts are exported.",
    )
    include_draft_status: bool = Field(
        default=False,
        description="Whether to include drafts that are still in Draft status. Approved drafts are always included.",
    )


class ExportListResponse(BaseModel):
    items: list[ExportResponse] = Field(description="Export batches returned for the current page.")
    meta: PaginationMeta = Field(description="Pagination information.")
