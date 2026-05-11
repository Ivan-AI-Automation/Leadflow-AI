from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import CurrentUserResponse
from app.services.auth_service import authenticate_user, create_token_response, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AuthResponse:
    user = register_user(db, request)
    token = create_token_response(user)
    return AuthResponse(user=CurrentUserResponse.model_validate(user), token=token)


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    user = authenticate_user(db, request)
    return create_token_response(user)


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(current_user)
