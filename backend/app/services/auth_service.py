from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AuthenticationError, ConflictError
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import create_user, get_user_by_email, get_user_by_id
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


def register_user(db: Session, request: RegisterRequest) -> User:
    existing_user = get_user_by_email(db, request.email)
    if existing_user is not None:
        raise ConflictError("A user with this email address already exists.")

    hashed_password = hash_password(request.password)
    return create_user(db, email=str(request.email), hashed_password=hashed_password)


def authenticate_user(db: Session, request: LoginRequest) -> User:
    user = get_user_by_email(db, request.email)
    if user is None or not verify_password(request.password, user.hashed_password):
        raise AuthenticationError("The email or password is incorrect.")

    if not user.is_active:
        raise AuthenticationError("This user account is inactive.")

    return user


def create_token_response(user: User) -> TokenResponse:
    settings = get_settings()
    access_token = create_access_token(subject=str(user.id))
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=settings.access_token_expire_minutes,
    )


def get_user_from_token(db: Session, token: str) -> User:
    payload = decode_access_token(token)

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("The access token contains an invalid user identifier.") from exc

    user = get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("The authenticated user could not be found.")

    return user
