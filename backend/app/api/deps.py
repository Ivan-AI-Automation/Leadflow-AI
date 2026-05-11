from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.errors import NotFoundError
from app.models.user import User
from app.services.auth_service import get_user_from_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    return get_user_from_token(db, token)


def ensure_current_user_owns_resource(current_user: User, resource_user_id: int) -> None:
    if current_user.id != resource_user_id:
        raise NotFoundError("The requested resource was not found.")
