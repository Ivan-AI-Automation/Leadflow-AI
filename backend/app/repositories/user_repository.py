from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.models.user import User


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized_email = normalize_email(email)
    statement = select(User).where(User.email == normalized_email)
    return db.scalar(statement)


def create_user(db: Session, *, email: str, hashed_password: str) -> User:
    user = User(
        email=normalize_email(email),
        hashed_password=hashed_password,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
