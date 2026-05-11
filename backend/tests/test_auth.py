from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
import app.models as _models  # noqa: F401


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def register_payload(email: str = "owner@example.com") -> dict[str, str]:
    return {
        "email": email,
        "password": "StrongPassword123",
    }


def test_register_user(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json=register_payload())

    assert response.status_code == 201
    payload = response.json()
    assert payload["user"]["email"] == "owner@example.com"
    assert payload["user"]["is_active"] is True
    assert "hashed_password" not in payload["user"]
    assert payload["token"]["access_token"]
    assert payload["token"]["token_type"] == "bearer"


def test_register_duplicate_email_returns_conflict(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=register_payload())

    response = client.post("/api/v1/auth/register", json=register_payload("OWNER@example.com"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_login_with_correct_password_returns_token(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=register_payload())

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "owner@example.com",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["token_type"] == "bearer"
    assert payload["expires_in_minutes"] > 0


def test_login_with_wrong_password_returns_unauthorized(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=register_payload())

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "owner@example.com",
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_error"


def test_get_current_user(client: TestClient) -> None:
    register_response = client.post("/api/v1/auth/register", json=register_payload())
    token = register_response.json()["token"]["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "owner@example.com"
    assert payload["is_active"] is True
