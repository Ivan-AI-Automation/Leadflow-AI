from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import CurrentUserResponse


class RegisterRequest(BaseModel):
    email: EmailStr = Field(description="Email address used to create the account.")
    password: str = Field(min_length=8, max_length=128, description="Account password.")


class LoginRequest(BaseModel):
    email: EmailStr = Field(description="Email address used to sign in.")
    password: str = Field(min_length=1, max_length=128, description="Account password.")


class TokenResponse(BaseModel):
    access_token: str = Field(description="JWT access token.")
    token_type: str = Field(default="bearer", description="Token type for authorization headers.")
    expires_in_minutes: int = Field(description="Number of minutes until the token expires.")


class AuthResponse(BaseModel):
    user: CurrentUserResponse = Field(description="Authenticated user.")
    token: TokenResponse = Field(description="Access token for API requests.")
