from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.common import ORMBaseModel


class CurrentUserResponse(ORMBaseModel):
    id: int = Field(description="Unique user identifier.")
    email: EmailStr = Field(description="User email address.")
    is_active: bool = Field(description="Whether the user account is active.")
    created_at: datetime = Field(description="Date and time when the user was created.")
