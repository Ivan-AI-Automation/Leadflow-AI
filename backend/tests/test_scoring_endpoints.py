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
from app.models.lead import Lead
from app.models.lead_score import LeadScore
import app.models as _models  # noqa: F401


@pytest.fixture()
def client_and_session(tmp_path: Path) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
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
    original_max_upload_size_mb = settings.max_upload_size_mb
    settings.upload_dir = tmp_path / "uploads"
    settings.max_upload_size_mb = 1

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client, testing_session_local

    app.dependency_overrides.clear()
    settings.upload_dir = original_upload_dir
    settings.max_upload_size_mb = original_max_upload_size_mb
    Base.metadata.drop_all(bind=engine)


def auth_header(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
        },
    )
    token = response.json()["token"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def upload_and_process_csv(client: TestClient, headers: dict[str, str], filename: str, content: bytes) -> int:
    upload_response = client.post(
        "/api/v1/imports/upload",
        headers=headers,
        files={"file": (filename, content, "text/csv")},
    )
    assert upload_response.status_code == 201
    import_id = int(upload_response.json()["id"])

    process_response = client.post(f"/api/v1/imports/{import_id}/process", headers=headers)
    assert process_response.status_code == 200
    return import_id


def scoring_sample_csv() -> bytes:
    return (
        b"first_name,last_name,company_name,job_title,email,phone,website,industry,"
        b"source,location,deal_value,budget_range,interest_level,timeline,notes\n"
        b"Maya,Patel,Northstar Homes,Operations Director,maya@example.com,+1 415 555 0134,"
        b"https://northstar.example,Property Management,Referral,San Francisco CA,32000,"
        b"25k-50k,High,Immediate,Asked for a proposal and wants onboarding next week.\n"
        b"Jordan,Lee,BrightPath Marketing,Founder,jordan@example.com,,,"
        b"Marketing Agency,Inbound form,Austin TX,9200,5k-10k,Medium,30-60 days,"
        b"Needs help cleaning CRM data before a new outbound campaign.\n"
        b"Liam,Owen,Small Consultancy,,,+1 512 555 0199,,,"
        b"Newsletter,Denver CO,,Under 5k,Medium,Next quarter,Asked for examples.\n"
        b"Casey,Moore,,,,,,,,,,,,,\n"
    )


def test_score_single_lead_saves_score_and_updates_lead(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session_local = client_and_session
    headers = auth_header(client, "owner@example.com")
    import_id = upload_and_process_csv(client, headers, "scoring_leads.csv", scoring_sample_csv())

    with testing_session_local() as db:
        lead = db.scalar(select(Lead).where(Lead.import_id == import_id).order_by(Lead.id))
        assert lead is not None
        lead_id = lead.id

    response = client.post(f"/api/v1/leads/{lead_id}/score", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["lead_id"] == lead_id
    assert payload["score"] == 95
    assert payload["category"] == "Hot"
    assert payload["score_breakdown_json"]["contact_completeness"] == 25

    get_response = client.get(f"/api/v1/leads/{lead_id}/score", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["score"] == 95

    with testing_session_local() as db:
        refreshed_lead = db.get(Lead, lead_id)
        saved_score = db.scalar(select(LeadScore).where(LeadScore.lead_id == lead_id))

    assert refreshed_lead is not None
    assert saved_score is not None
    assert refreshed_lead.priority_score == 95
    assert refreshed_lead.category == "Hot"
    assert saved_score.category == "Hot"


def test_score_import_leads_returns_category_summary(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    headers = auth_header(client, "owner@example.com")
    import_id = upload_and_process_csv(client, headers, "scoring_leads.csv", scoring_sample_csv())

    response = client.post(f"/api/v1/imports/{import_id}/score", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "total_scored": 4,
        "hot_count": 1,
        "warm_count": 1,
        "nurture_count": 1,
        "low_priority_count": 1,
    }


def test_score_all_leads_scores_only_current_user_leads(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    owner_headers = auth_header(client, "owner@example.com")
    other_headers = auth_header(client, "other@example.com")
    upload_and_process_csv(client, owner_headers, "owner_scoring_leads.csv", scoring_sample_csv())
    upload_and_process_csv(
        client,
        other_headers,
        "other_scoring_leads.csv",
        b"first_name,last_name,email,phone\nOther,User,other.lead@example.com,+1 202 555 0101\n",
    )

    response = client.post("/api/v1/leads/score-all", headers=owner_headers)

    assert response.status_code == 200
    assert response.json()["total_scored"] == 4


def test_user_cannot_score_another_users_lead_or_import(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session_local = client_and_session
    owner_headers = auth_header(client, "owner@example.com")
    other_headers = auth_header(client, "other@example.com")
    import_id = upload_and_process_csv(client, owner_headers, "scoring_leads.csv", scoring_sample_csv())

    with testing_session_local() as db:
        lead = db.scalar(select(Lead).where(Lead.import_id == import_id).order_by(Lead.id))
        assert lead is not None
        lead_id = lead.id

    lead_response = client.post(f"/api/v1/leads/{lead_id}/score", headers=other_headers)
    import_response = client.post(f"/api/v1/imports/{import_id}/score", headers=other_headers)

    assert lead_response.status_code == 404
    assert lead_response.json()["error"]["code"] == "not_found"
    assert import_response.status_code == 404
    assert import_response.json()["error"]["code"] == "not_found"


def test_get_score_before_scoring_returns_not_found(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session_local = client_and_session
    headers = auth_header(client, "owner@example.com")
    import_id = upload_and_process_csv(client, headers, "scoring_leads.csv", scoring_sample_csv())

    with testing_session_local() as db:
        lead = db.scalar(select(Lead).where(Lead.import_id == import_id).order_by(Lead.id))
        assert lead is not None
        lead_id = lead.id

    response = client.get(f"/api/v1/leads/{lead_id}/score", headers=headers)

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "This lead has not been scored yet."
