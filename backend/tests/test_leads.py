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
from app.models.lead_activity import LeadActivity
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


def auth_header(client: TestClient, email: str = "owner@example.com") -> dict[str, str]:
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


def test_create_get_update_and_delete_lead(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    headers = auth_header(client)

    created = create_lead(
        client,
        headers,
        {
            "first_name": "Maya",
            "last_name": "Patel",
            "company_name": "Northstar Homes",
            "job_title": "Operations Director",
            "email": "maya@example.com",
            "phone": "+14155550134",
            "website": "https://northstar.example",
            "industry": "Property Management",
            "source": "Referral",
            "location": "San Francisco, CA",
            "deal_value": "18500",
            "budget_range": "15k-25k",
            "interest_level": "High",
            "timeline": "This month",
            "notes": "Asked for a proposal.",
        },
    )
    lead_id = created["id"]

    get_response = client.get(f"/api/v1/leads/{lead_id}", headers=headers)
    patch_response = client.patch(
        f"/api/v1/leads/{lead_id}",
        headers=headers,
        json={
            "phone": "+14155559999",
            "category": "Warm",
            "priority_score": 72,
        },
    )
    delete_response = client.delete(f"/api/v1/leads/{lead_id}", headers=headers)
    missing_response = client.get(f"/api/v1/leads/{lead_id}", headers=headers)

    assert get_response.status_code == 200
    assert get_response.json()["email"] == "maya@example.com"
    assert patch_response.status_code == 200
    assert patch_response.json()["phone"] == "+14155559999"
    assert patch_response.json()["category"] == "Warm"
    assert patch_response.json()["priority_score"] == 72
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Lead deleted successfully."
    assert missing_response.status_code == 404


def test_list_leads_supports_filters_pagination_and_sorting(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    headers = auth_header(client)
    hot = create_lead(
        client,
        headers,
        {
            "first_name": "Maya",
            "last_name": "Patel",
            "company_name": "Northstar Homes",
            "email": "maya@example.com",
            "phone": "+14155550134",
            "industry": "Property Management",
            "source": "Referral",
            "location": "San Francisco, CA",
        },
    )
    warm = create_lead(
        client,
        headers,
        {
            "first_name": "Jordan",
            "last_name": "Lee",
            "company_name": "BrightPath Marketing",
            "email": "jordan@example.com",
            "industry": "Marketing Agency",
            "source": "Inbound form",
            "location": "Austin, TX",
        },
    )
    low = create_lead(
        client,
        headers,
        {
            "first_name": "Liam",
            "last_name": "Owen",
            "company_name": "Small Consultancy",
            "phone": "+15125550199",
            "industry": "Consulting",
            "source": "Newsletter",
            "location": "Denver, CO",
        },
    )

    client.patch(f"/api/v1/leads/{hot['id']}", headers=headers, json={"category": "Hot", "priority_score": 91})
    client.patch(f"/api/v1/leads/{warm['id']}", headers=headers, json={"category": "Warm", "priority_score": 68})
    client.patch(f"/api/v1/leads/{low['id']}", headers=headers, json={"category": "Low Priority", "priority_score": 28})

    hot_response = client.get("/api/v1/leads?category=Hot", headers=headers)
    missing_email_response = client.get("/api/v1/leads?missing_email=true", headers=headers)
    search_response = client.get("/api/v1/leads?search=brightpath", headers=headers)
    sorted_response = client.get(
        "/api/v1/leads?sort_by=priority_score&sort_order=desc&limit=2&offset=0",
        headers=headers,
    )

    assert hot_response.status_code == 200
    assert hot_response.json()["meta"]["total"] == 1
    assert hot_response.json()["items"][0]["company_name"] == "Northstar Homes"
    assert missing_email_response.json()["meta"]["total"] == 1
    assert missing_email_response.json()["items"][0]["first_name"] == "Liam"
    assert search_response.json()["meta"]["total"] == 1
    assert search_response.json()["items"][0]["first_name"] == "Jordan"
    assert sorted_response.json()["meta"] == {"total": 3, "limit": 2, "offset": 0}
    assert [item["priority_score"] for item in sorted_response.json()["items"]] == [91, 68]


def test_status_update_creates_activity(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session_local = client_and_session
    headers = auth_header(client)
    lead = create_lead(
        client,
        headers,
        {
            "first_name": "Maya",
            "last_name": "Patel",
            "email": "maya@example.com",
        },
    )

    response = client.patch(
        f"/api/v1/leads/{lead['id']}/status",
        headers=headers,
        json={"status": "Contacted"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Contacted"

    with testing_session_local() as db:
        activity = db.scalar(select(LeadActivity).where(LeadActivity.lead_id == lead["id"]))

    assert activity is not None
    assert activity.activity_type == "status_changed"
    assert activity.description == "Status changed from New to Contacted."


def test_user_can_access_only_their_own_leads(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    owner_headers = auth_header(client, "owner@example.com")
    other_headers = auth_header(client, "other@example.com")
    lead = create_lead(
        client,
        owner_headers,
        {
            "first_name": "Maya",
            "last_name": "Patel",
            "email": "maya@example.com",
        },
    )

    get_response = client.get(f"/api/v1/leads/{lead['id']}", headers=other_headers)
    patch_response = client.patch(
        f"/api/v1/leads/{lead['id']}",
        headers=other_headers,
        json={"first_name": "Changed"},
    )
    delete_response = client.delete(f"/api/v1/leads/{lead['id']}", headers=other_headers)

    assert get_response.status_code == 404
    assert patch_response.status_code == 404
    assert delete_response.status_code == 404


def test_status_filter_and_score_range_filter(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    headers = auth_header(client)
    first = create_lead(
        client,
        headers,
        {
            "first_name": "Maya",
            "last_name": "Patel",
            "email": "maya@example.com",
        },
    )
    second = create_lead(
        client,
        headers,
        {
            "first_name": "Jordan",
            "last_name": "Lee",
            "email": "jordan@example.com",
        },
    )

    client.patch(f"/api/v1/leads/{first['id']}", headers=headers, json={"priority_score": 82})
    client.patch(f"/api/v1/leads/{second['id']}", headers=headers, json={"priority_score": 45})
    client.patch(f"/api/v1/leads/{first['id']}/status", headers=headers, json={"status": "Follow-up"})

    response = client.get(
        "/api/v1/leads?status=Follow-up&min_score=80&max_score=100",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 1
    assert response.json()["items"][0]["first_name"] == "Maya"
