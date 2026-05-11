from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMBaseModel


class LeadImportResponse(ORMBaseModel):
    id: int = Field(description="Unique import identifier.")
    user_id: int = Field(description="Identifier of the user who uploaded the file.")
    original_filename: str = Field(description="Original uploaded filename.")
    stored_filename: str = Field(description="Internal stored filename.")
    file_type: str = Field(description="Uploaded file type, such as csv or xlsx.")
    rows_count: int = Field(ge=0, description="Number of rows found in the uploaded file.")
    columns_count: int = Field(ge=0, description="Number of columns found in the uploaded file.")
    columns_json: list[str] = Field(description="Column names detected in the uploaded file.")
    dtypes_json: dict[str, str] = Field(description="Basic pandas data type information by column.")
    status: str = Field(description="Processing status of the import.")
    created_at: datetime = Field(description="Date and time when the import was created.")


class LeadImportProcessResponse(BaseModel):
    import_id: int = Field(description="Processed import identifier.")
    status: str = Field(description="Final processing status.")
    dataset_type: str = Field(description="Detected lead dataset type.")
    created_leads_count: int = Field(ge=0, description="Number of Lead records created.")
    skipped_rows_count: int = Field(ge=0, description="Number of empty rows skipped.")
    row_count: int = Field(ge=0, description="Number of usable rows processed.")
    missing_email_count: int = Field(ge=0, description="Number of processed leads missing email.")
    missing_phone_count: int = Field(ge=0, description="Number of processed leads missing phone.")
    missing_company_count: int = Field(ge=0, description="Number of processed leads missing company name.")
    duplicate_lead_count: int = Field(ge=0, description="Number of duplicate-looking rows detected.")
    critical_missing_fields: dict[str, int] = Field(description="Required fields with missing value counts.")
    quality_score: int = Field(ge=0, le=100, description="Import quality score from 0 to 100.")
    readable_summary: str = Field(description="Business-readable processing summary.")
