from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.email_draft import EmailDraft
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
    settings.upload_dir = tmp_path / "uploads"

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


def create_lead(client: TestClient, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
    response = client.post("/api/v1/leads", headers=headers, json=payload)
    assert response.status_code == 201
    return response.json()


def patch_lead(
    client: TestClient, headers: dict[str, str], lead_id: int, payload: dict[str, object]
) -> dict[str, object]:
    response = client.patch(f"/api/v1/leads/{lead_id}", headers=headers, json=payload)
    assert response.status_code == 200
    return response.json()


def test_dashboard_handles_user_with_no_leads(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    headers = auth_header(client, "empty@example.com")

    summary_response = client.get("/api/v1/dashboard/summary", headers=headers)
    charts_response = client.get("/api/v1/dashboard/charts", headers=headers)

    assert summary_response.status_code == 200
    assert summary_response.json() == {
        "total_leads": 0,
        "new_leads": 0,
        "contacted_leads": 0,
        "follow_up_leads": 0,
        "closed_leads": 0,
        "lost_leads": 0,
        "hot_leads": 0,
        "warm_leads": 0,
        "nurture_leads": 0,
        "low_priority_leads": 0,
        "missing_email_count": 0,
        "missing_phone_count": 0,
        "average_priority_score": 0.0,
        "drafts_created": 0,
        "drafts_approved": 0,
    }
    assert charts_response.status_code == 200
    assert charts_response.json()["charts"][0]["y"] == [0, 0, 0, 0, 0]
    assert charts_response.json()["charts"][1]["values"] == [0, 0, 0, 0]


def test_dashboard_summary_and_charts_are_scoped_to_current_user(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session_local = client_and_session
    owner_headers = auth_header(client, "owner@example.com")
    other_headers = auth_header(client, "other@example.com")

    hot = create_lead(
        client,
        owner_headers,
        {
            "first_name": "Maya",
            "last_name": "Patel",
            "email": "maya@example.com",
            "phone": "+14155550134",
            "company_name": "Northstar Homes",
        },
    )
    warm = create_lead(
        client,
        owner_headers,
        {
            "first_name": "Jordan",
            "last_name": "Lee",
            "email": "jordan@example.com",
            "company_name": "BrightPath Marketing",
        },
    )
    nurture = create_lead(
        client,
        owner_headers,
        {
            "first_name": "Liam",
            "last_name": "Owen",
            "phone": "+15125550199",
            "company_name": "Small Consultancy",
        },
    )
    low = create_lead(
        client,
        owner_headers,
        {
            "first_name": "Casey",
            "last_name": "Moore",
        },
    )

    patch_lead(client, owner_headers, hot["id"], {"category": "Hot", "priority_score": 95})
    patch_lead(client, owner_headers, warm["id"], {"category": "Warm", "priority_score": 68})
    patch_lead(client, owner_headers, nurture["id"], {"category": "Nurture", "priority_score": 45})
    patch_lead(client, owner_headers, low["id"], {"category": "Low Priority", "priority_score": 22})
    client.patch(f"/api/v1/leads/{warm['id']}/status", headers=owner_headers, json={"status": "Contacted"})
    client.patch(f"/api/v1/leads/{nurture['id']}/status", headers=owner_headers, json={"status": "Follow-up"})
    client.patch(f"/api/v1/leads/{low['id']}/status", headers=owner_headers, json={"status": "Lost"})

    create_lead(
        client,
        other_headers,
        {
            "first_name": "Other",
            "last_name": "User",
            "email": "other.lead@example.com",
        },
    )

    with testing_session_local() as db:
        db.add_all(
            [
                EmailDraft(
                    user_id=1,
                    lead_id=hot["id"],
                    subject="Follow up",
                    body="Hello Maya",
                    tone="professional",
                    status="Draft",
                    ai_provider="mock",
                ),
                EmailDraft(
                    user_id=1,
                    lead_id=warm["id"],
                    subject="Next steps",
                    body="Hello Jordan",
                    tone="professional",
                    status="Approved",
                    ai_provider="mock",
                ),
                EmailDraft(
                    user_id=2,
                    lead_id=5,
                    subject="Other",
                    body="Other user",
                    tone="professional",
                    status="Approved",
                    ai_provider="mock",
                ),
            ]
        )
        db.commit()

    summary_response = client.get("/api/v1/dashboard/summary", headers=owner_headers)
    charts_response = client.get("/api/v1/dashboard/charts", headers=owner_headers)

    assert summary_response.status_code == 200
    assert summary_response.json() == {
        "total_leads": 4,
        "new_leads": 1,
        "contacted_leads": 1,
        "follow_up_leads": 1,
        "closed_leads": 0,
        "lost_leads": 1,
        "hot_leads": 1,
        "warm_leads": 1,
        "nurture_leads": 1,
        "low_priority_leads": 1,
        "missing_email_count": 2,
        "missing_phone_count": 2,
        "average_priority_score": 57.5,
        "drafts_created": 2,
        "drafts_approved": 1,
    }
    assert charts_response.status_code == 200
    assert charts_response.json() == {
        "charts": [
            {
                "id": "leads_by_status",
                "title": "Leads by Status",
                "type": "bar",
                "x": ["New", "Contacted", "Follow-up", "Closed", "Lost"],
                "y": [1, 1, 1, 0, 1],
            },
            {
                "id": "leads_by_category",
                "title": "Leads by Category",
                "type": "pie",
                "labels": ["Hot", "Warm", "Nurture", "Low Priority"],
                "values": [1, 1, 1, 1],
            },
        ]
    }


def test_dashboard_for_other_user_does_not_include_owner_data(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    owner_headers = auth_header(client, "owner@example.com")
    other_headers = auth_header(client, "other@example.com")

    create_lead(
        client,
        owner_headers,
        {
            "first_name": "Maya",
            "last_name": "Patel",
            "email": "maya@example.com",
        },
    )

    response = client.get("/api/v1/dashboard/summary", headers=other_headers)

    assert response.status_code == 200
    assert response.json()["total_leads"] == 0
