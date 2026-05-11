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


def upload_csv(client: TestClient, headers: dict[str, str], filename: str, content: bytes) -> int:
    response = client.post(
        "/api/v1/imports/upload",
        headers=headers,
        files={"file": (filename, content, "text/csv")},
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def test_process_import_creates_leads_and_marks_import_processed(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session_local = client_and_session
    headers = auth_header(client, "owner@example.com")
    import_id = upload_csv(
        client,
        headers,
        "b2b_leads.csv",
        (
            b"first_name,last_name,company_name,job_title,email,phone,website,industry,"
            b"source,location,deal_value,budget_range,interest_level,timeline,notes\n"
            b"Maya,Patel,Northstar Homes,Operations Director,maya@example.com,+1 415 555 0134,"
            b"https://northstar.example,Property Management,Referral,San Francisco CA,18500,"
            b"15k - 25k,High,30 to 60 days,Asked for a proposal.\n"
            b"Jordan,Lee,BrightPath Marketing,Founder,,+1 512 555 0199,"
            b"https://brightpath.example,Marketing Agency,Inbound form,Austin TX,9200,"
            b"5k-10k,Medium,This quarter,Needs CRM cleanup.\n"
            b",,,,,,,,,,,,,,\n"
        ),
    )

    response = client.post(f"/api/v1/imports/{import_id}/process", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["import_id"] == import_id
    assert payload["status"] == "processed"
    assert payload["dataset_type"] == "b2b_service"
    assert payload["created_leads_count"] == 2
    assert payload["skipped_rows_count"] == 1
    assert payload["missing_email_count"] == 1
    assert "Created 2 lead records" in payload["readable_summary"]

    import_response = client.get(f"/api/v1/imports/{import_id}", headers=headers)
    assert import_response.json()["status"] == "processed"

    with testing_session_local() as db:
        leads = list(db.scalars(select(Lead).order_by(Lead.id)).all())

    assert len(leads) == 2
    assert leads[0].first_name == "Maya"
    assert leads[0].email == "maya@example.com"
    assert leads[0].phone == "+14155550134"
    assert str(leads[0].deal_value) == "18500.00"
    assert leads[0].budget_range == "15k-25k"
    assert leads[0].timeline == "30-60 days"
    assert leads[0].missing_fields_json == []
    assert leads[1].email is None
    assert leads[1].missing_fields_json == ["email"]


def test_process_recruitment_import_preserves_dataset_specific_fields_in_notes(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session_local = client_and_session
    headers = auth_header(client, "recruiter@example.com")
    import_id = upload_csv(
        client,
        headers,
        "recruitment_leads.csv",
        (
            b"first_name,last_name,company_name,job_title,email,phone,hiring_need,"
            b"role_type,urgency,source,location,notes\n"
            b"Amelia,Foster,Vertex Payments,People Director,amelia@example.com,"
            b"+44 20 5555 0141,Senior backend engineer,Permanent,High,Referral,"
            b"London UK,Needs shortlist within two weeks.\n"
        ),
    )

    response = client.post(f"/api/v1/imports/{import_id}/process", headers=headers)

    assert response.status_code == 200
    assert response.json()["dataset_type"] == "recruitment"

    with testing_session_local() as db:
        lead = db.scalar(select(Lead).where(Lead.import_id == import_id))

    assert lead is not None
    assert lead.industry == "Recruitment"
    assert lead.interest_level == "High"
    assert "Hiring need: Senior backend engineer." in str(lead.notes)
    assert "Role type: Permanent." in str(lead.notes)
    assert "Urgency: High." in str(lead.notes)


def test_process_import_is_limited_to_owner(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    owner_headers = auth_header(client, "owner@example.com")
    other_headers = auth_header(client, "other@example.com")
    import_id = upload_csv(
        client,
        owner_headers,
        "owner_leads.csv",
        b"first_name,last_name,email,phone\nMaya,Patel,maya@example.com,+1 415 555 0134\n",
    )

    response = client.post(f"/api/v1/imports/{import_id}/process", headers=other_headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_process_import_can_be_run_again_without_creating_duplicate_records(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session_local = client_and_session
    headers = auth_header(client, "owner@example.com")
    import_id = upload_csv(
        client,
        headers,
        "simple_leads.csv",
        b"first_name,last_name,email,phone\nMaya,Patel,maya@example.com,+1 415 555 0134\n",
    )

    first_response = client.post(f"/api/v1/imports/{import_id}/process", headers=headers)
    second_response = client.post(f"/api/v1/imports/{import_id}/process", headers=headers)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["created_leads_count"] == 1

    with testing_session_local() as db:
        lead_count = len(list(db.scalars(select(Lead)).all()))

    assert lead_count == 1
