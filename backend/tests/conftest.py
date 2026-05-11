from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.email_draft import EmailDraft
from app.models.lead import Lead
from app.models.lead_score import LeadScore
import app.models as _models  # noqa: F401

TEST_PASSWORD = "StrongPassword123"


@pytest.fixture()
def test_db_session_factory(tmp_path: Path) -> Generator[sessionmaker[Session], None, None]:
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

    settings = get_settings()
    original_upload_dir = settings.upload_dir
    original_export_dir = settings.export_dir
    original_max_upload_size_mb = settings.max_upload_size_mb
    original_ai_provider = settings.ai_provider

    settings.upload_dir = tmp_path / "uploads"
    settings.export_dir = tmp_path / "exports"
    settings.max_upload_size_mb = 1
    settings.ai_provider = "mock"
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.export_dir.mkdir(parents=True, exist_ok=True)

    try:
        yield testing_session_local
    finally:
        settings.upload_dir = original_upload_dir
        settings.export_dir = original_export_dir
        settings.max_upload_size_mb = original_max_upload_size_mb
        settings.ai_provider = original_ai_provider
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(test_db_session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = test_db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def test_db(client: TestClient, test_db_session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    db = test_db_session_factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def registered_user_payload(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@example.com",
            "password": TEST_PASSWORD,
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture()
def test_user(registered_user_payload: dict[str, object]) -> dict[str, object]:
    user = registered_user_payload["user"]
    assert isinstance(user, dict)
    return user


@pytest.fixture()
def auth_token(registered_user_payload: dict[str, object]) -> str:
    token = registered_user_payload["token"]
    assert isinstance(token, dict)
    return str(token["access_token"])


@pytest.fixture()
def auth_headers(auth_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture()
def sample_import_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "realistic_b2b_leads.csv"
    file_path.write_text(
        "\n".join(
            [
                "first_name,last_name,company_name,job_title,email,phone,website,industry,source,location,"
                "deal_value,budget_range,interest_level,timeline,notes",
                "Maya,Patel,Northstar Homes,Operations Director,maya@example.com,+1 415 555 0134,"
                "https://northstar.example,Property Management,Referral,San Francisco CA,32000,25k-50k,"
                "High,Immediate,Asked for a proposal and wants onboarding next week.",
                "Jordan,Lee,BrightPath Marketing,Founder,jordan@example.com,,https://brightpath.example,"
                "Marketing Agency,Inbound form,Austin TX,9200,5k-10k,Medium,30-60 days,"
                "Needs help cleaning CRM data before a new outbound campaign.",
                "Liam,Owen,Small Consultancy,,,+1 512 555 0199,,Consulting,Newsletter,Denver CO,,"
                "Under 5k,Medium,Next quarter,Asked for examples.",
            ]
        ),
        encoding="utf-8",
    )
    return file_path


@pytest.fixture()
def uploaded_import(client: TestClient, auth_headers: dict[str, str], sample_import_file: Path) -> dict[str, object]:
    with sample_import_file.open("rb") as file_handle:
        response = client.post(
            "/api/v1/imports/upload",
            headers=auth_headers,
            files={"file": (sample_import_file.name, file_handle, "text/csv")},
        )
    assert response.status_code == 201
    return response.json()


@pytest.fixture()
def processed_leads(
    client: TestClient,
    auth_headers: dict[str, str],
    uploaded_import: dict[str, object],
    test_db: Session,
) -> list[Lead]:
    import_id = int(uploaded_import["id"])
    response = client.post(f"/api/v1/imports/{import_id}/process", headers=auth_headers)
    assert response.status_code == 200

    leads = list(test_db.scalars(select(Lead).where(Lead.import_id == import_id).order_by(Lead.id)).all())
    assert len(leads) == 3
    return leads


@pytest.fixture()
def scored_leads(
    client: TestClient, auth_headers: dict[str, str], processed_leads: list[Lead], test_db: Session
) -> list[Lead]:
    response = client.post("/api/v1/leads/score-all", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total_scored"] == len(processed_leads)

    test_db.expire_all()
    scored = list(test_db.scalars(select(Lead).order_by(Lead.id)).all())
    assert all(lead.priority_score >= 0 for lead in scored)
    return scored


@pytest.fixture()
def email_draft(
    client: TestClient, auth_headers: dict[str, str], scored_leads: list[Lead], test_db: Session
) -> EmailDraft:
    lead = next(lead for lead in scored_leads if lead.email)
    response = client.post(
        f"/api/v1/leads/{lead.id}/email-draft",
        headers=auth_headers,
        json={
            "tone": "Professional",
            "sender_company_name": "LeadFlow AI",
        },
    )
    assert response.status_code == 201

    draft = test_db.scalar(select(EmailDraft).where(EmailDraft.id == response.json()["id"]))
    assert draft is not None
    return draft


@pytest.fixture()
def approved_email_draft(
    client: TestClient, auth_headers: dict[str, str], email_draft: EmailDraft, test_db: Session
) -> EmailDraft:
    response = client.patch(f"/api/v1/email-drafts/{email_draft.id}/approve", headers=auth_headers)
    assert response.status_code == 200

    test_db.expire_all()
    draft = test_db.get(EmailDraft, email_draft.id)
    assert draft is not None
    assert draft.status == "Approved"
    return draft


@pytest.fixture()
def saved_lead_scores(scored_leads: list[Lead], test_db: Session) -> list[LeadScore]:
    scores = list(test_db.scalars(select(LeadScore).order_by(LeadScore.id)).all())
    assert len(scores) == len(scored_leads)
    return scores
