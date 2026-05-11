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
    original_ai_provider = settings.ai_provider
    settings.upload_dir = tmp_path / "uploads"
    settings.ai_provider = "mock"

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
    settings.ai_provider = original_ai_provider
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


def generate_draft(
    client: TestClient,
    headers: dict[str, str],
    lead_id: int,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/leads/{lead_id}/email-draft",
        headers=headers,
        json=payload or {"tone": "Professional"},
    )
    assert response.status_code == 201
    return response.json()


def test_generate_single_email_draft_creates_draft_and_activity(
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
            "company_name": "Northstar Homes",
            "email": "maya@example.com",
            "industry": "Property Management",
            "source": "Referral",
            "interest_level": "High",
            "timeline": "This month",
            "notes": "Asked for a concise proposal.",
            "category": "Hot",
            "priority_score": 92,
        },
    )

    response = client.post(
        f"/api/v1/leads/{lead['id']}/email-draft",
        headers=headers,
        json={
            "tone": "Warm",
            "business_type": "B2B service business",
            "sender_company_name": "LeadFlow AI",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["lead_id"] == lead["id"]
    assert payload["tone"] == "Warm"
    assert payload["status"] == "Draft"
    assert payload["ai_provider"] == "mock"
    assert payload["subject"] == "Following up with Northstar Homes"
    assert "Hi Maya" in payload["body"]
    assert "LeadFlow AI" in payload["body"]

    with testing_session_local() as db:
        draft = db.scalar(select(EmailDraft).where(EmailDraft.lead_id == lead["id"]))
        activity = db.scalar(select(LeadActivity).where(LeadActivity.lead_id == lead["id"]))

    assert draft is not None
    assert draft.subject == "Following up with Northstar Homes"
    assert activity is not None
    assert activity.activity_type == "email_draft_generated"
    assert activity.description == "Email draft generated."


def test_generate_email_draft_requires_lead_email(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    headers = auth_header(client)
    lead = create_lead(
        client,
        headers,
        {
            "first_name": "Liam",
            "last_name": "Owen",
            "company_name": "Small Consultancy",
            "phone": "+15125550199",
        },
    )

    response = client.post(
        f"/api/v1/leads/{lead['id']}/email-draft",
        headers=headers,
        json={"tone": "Professional"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "does not have an email address" in response.json()["error"]["message"]


def test_generate_email_draft_does_not_overwrite_existing_draft_by_default(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    headers = auth_header(client)
    lead = create_lead(
        client,
        headers,
        {
            "first_name": "Jordan",
            "last_name": "Lee",
            "company_name": "BrightPath Marketing",
            "email": "jordan@example.com",
        },
    )

    first_response = client.post(
        f"/api/v1/leads/{lead['id']}/email-draft",
        headers=headers,
        json={"tone": "Professional"},
    )
    second_response = client.post(
        f"/api/v1/leads/{lead['id']}/email-draft",
        headers=headers,
        json={"tone": "Friendly"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["error"]["code"] == "conflict"


def test_generate_email_draft_can_explicitly_replace_existing_draft(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session_local = client_and_session
    headers = auth_header(client)
    lead = create_lead(
        client,
        headers,
        {
            "first_name": "Avery",
            "last_name": "Stone",
            "company_name": "Vertex Payments",
            "email": "avery@example.com",
        },
    )

    first_response = client.post(
        f"/api/v1/leads/{lead['id']}/email-draft",
        headers=headers,
        json={"tone": "Professional"},
    )
    replace_response = client.post(
        f"/api/v1/leads/{lead['id']}/email-draft",
        headers=headers,
        json={
            "tone": "Short",
            "overwrite_existing": True,
        },
    )

    assert first_response.status_code == 201
    assert replace_response.status_code == 201
    assert replace_response.json()["id"] == first_response.json()["id"]
    assert replace_response.json()["tone"] == "Short"

    with testing_session_local() as db:
        draft_count = len(db.scalars(select(EmailDraft).where(EmailDraft.lead_id == lead["id"])).all())
        activities = list(db.scalars(select(LeadActivity).where(LeadActivity.lead_id == lead["id"])).all())

    assert draft_count == 1
    assert [activity.description for activity in activities] == [
        "Email draft generated.",
        "Email draft replaced.",
    ]


def test_bulk_email_drafts_create_and_skip_with_business_reasons(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    headers = auth_header(client)
    ready = create_lead(
        client,
        headers,
        {
            "first_name": "Maya",
            "last_name": "Patel",
            "company_name": "Northstar Homes",
            "email": "maya@example.com",
        },
    )
    missing_email = create_lead(
        client,
        headers,
        {
            "first_name": "Liam",
            "last_name": "Owen",
            "company_name": "Small Consultancy",
            "phone": "+15125550199",
        },
    )
    existing = create_lead(
        client,
        headers,
        {
            "first_name": "Jordan",
            "last_name": "Lee",
            "company_name": "BrightPath Marketing",
            "email": "jordan@example.com",
        },
    )
    client.post(
        f"/api/v1/leads/{existing['id']}/email-draft",
        headers=headers,
        json={"tone": "Professional"},
    )

    response = client.post(
        "/api/v1/email-drafts/bulk",
        headers=headers,
        json={
            "lead_ids": [ready["id"], missing_email["id"], existing["id"], ready["id"], 9999],
            "tone": "Direct",
            "sender_company_name": "LeadFlow AI",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["created_count"] == 1
    assert payload["skipped_count"] == 4
    assert payload["drafts"][0]["lead_id"] == ready["id"]
    assert payload["drafts"][0]["tone"] == "Direct"
    assert payload["skipped"] == [
        {
            "lead_id": missing_email["id"],
            "reason": "Lead does not have an email address.",
        },
        {
            "lead_id": existing["id"],
            "reason": "Lead already has an email draft.",
        },
        {
            "lead_id": ready["id"],
            "reason": "Lead was selected more than once.",
        },
        {
            "lead_id": 9999,
            "reason": "Lead was not found.",
        },
    ]


def test_user_cannot_generate_draft_for_another_users_lead(
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

    response = client.post(
        f"/api/v1/leads/{lead['id']}/email-draft",
        headers=other_headers,
        json={"tone": "Professional"},
    )

    assert response.status_code == 404


def test_list_email_drafts_supports_filters_pagination_and_sorting(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    headers = auth_header(client)
    hot_lead = create_lead(
        client,
        headers,
        {
            "first_name": "Maya",
            "last_name": "Patel",
            "company_name": "Northstar Homes",
            "email": "maya@example.com",
        },
    )
    warm_lead = create_lead(
        client,
        headers,
        {
            "first_name": "Jordan",
            "last_name": "Lee",
            "company_name": "BrightPath Marketing",
            "email": "jordan@example.com",
        },
    )
    client.patch(f"/api/v1/leads/{hot_lead['id']}", headers=headers, json={"category": "Hot", "priority_score": 91})
    client.patch(f"/api/v1/leads/{warm_lead['id']}", headers=headers, json={"category": "Warm", "priority_score": 68})

    hot_draft = generate_draft(client, headers, hot_lead["id"], {"tone": "Warm"})
    warm_draft = generate_draft(client, headers, warm_lead["id"], {"tone": "Direct"})
    client.patch(f"/api/v1/email-drafts/{hot_draft['id']}/approve", headers=headers)

    list_response = client.get("/api/v1/email-drafts?sort_by=created_at&sort_order=desc", headers=headers)
    status_response = client.get("/api/v1/email-drafts?status=Approved", headers=headers)
    tone_response = client.get("/api/v1/email-drafts?tone=Direct", headers=headers)
    category_response = client.get("/api/v1/email-drafts?lead_category=Hot", headers=headers)
    search_response = client.get("/api/v1/email-drafts?search=brightpath", headers=headers)
    paged_response = client.get("/api/v1/email-drafts?limit=1&offset=1", headers=headers)

    assert list_response.status_code == 200
    assert list_response.json()["meta"] == {"total": 2, "limit": 50, "offset": 0}
    assert {item["id"] for item in list_response.json()["items"]} == {hot_draft["id"], warm_draft["id"]}
    assert status_response.json()["meta"]["total"] == 1
    assert status_response.json()["items"][0]["id"] == hot_draft["id"]
    assert tone_response.json()["meta"]["total"] == 1
    assert tone_response.json()["items"][0]["id"] == warm_draft["id"]
    assert category_response.json()["meta"]["total"] == 1
    assert category_response.json()["items"][0]["id"] == hot_draft["id"]
    assert search_response.json()["meta"]["total"] == 1
    assert search_response.json()["items"][0]["id"] == warm_draft["id"]
    assert paged_response.json()["meta"] == {"total": 2, "limit": 1, "offset": 1}


def test_get_update_and_approve_email_draft(
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
            "company_name": "Northstar Homes",
            "email": "maya@example.com",
        },
    )
    draft = generate_draft(client, headers, lead["id"], {"tone": "Professional"})

    get_response = client.get(f"/api/v1/email-drafts/{draft['id']}", headers=headers)
    update_response = client.patch(
        f"/api/v1/email-drafts/{draft['id']}",
        headers=headers,
        json={
            "subject": "Updated follow-up",
            "body": "Hi Maya,\n\nHere is a cleaner draft.\n\nBest,",
            "tone": "Friendly",
        },
    )
    approve_response = client.patch(f"/api/v1/email-drafts/{draft['id']}/approve", headers=headers)

    assert get_response.status_code == 200
    assert get_response.json()["id"] == draft["id"]
    assert update_response.status_code == 200
    assert update_response.json()["subject"] == "Updated follow-up"
    assert update_response.json()["body"] == "Hi Maya,\n\nHere is a cleaner draft.\n\nBest,"
    assert update_response.json()["tone"] == "Friendly"
    assert update_response.json()["status"] == "Draft"
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "Approved"

    with testing_session_local() as db:
        activities = list(db.scalars(select(LeadActivity).where(LeadActivity.lead_id == lead["id"])).all())

    assert [activity.activity_type for activity in activities] == [
        "email_draft_generated",
        "email_draft_edited",
        "email_draft_approved",
    ]


def test_rewrite_email_draft_is_explicit_and_keeps_draft_unsent(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session_local = client_and_session
    headers = auth_header(client)
    lead = create_lead(
        client,
        headers,
        {
            "first_name": "Jordan",
            "last_name": "Lee",
            "company_name": "BrightPath Marketing",
            "email": "jordan@example.com",
        },
    )
    draft = generate_draft(client, headers, lead["id"], {"tone": "Professional"})

    response = client.post(
        f"/api/v1/email-drafts/{draft['id']}/rewrite",
        headers=headers,
        json={
            "tone": "Short",
            "sender_company_name": "LeadFlow AI",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == draft["id"]
    assert payload["tone"] == "Short"
    assert payload["status"] == "Draft"
    assert "business-friendly tone" in payload["body"]

    with testing_session_local() as db:
        activity = db.scalar(
            select(LeadActivity).where(
                LeadActivity.lead_id == lead["id"], LeadActivity.activity_type == "email_draft_rewritten"
            )
        )

    assert activity is not None
    assert activity.description == "Email draft rewritten with Short tone."


def test_delete_email_draft_archives_it(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session_local = client_and_session
    headers = auth_header(client)
    lead = create_lead(
        client,
        headers,
        {
            "first_name": "Avery",
            "last_name": "Stone",
            "company_name": "Vertex Payments",
            "email": "avery@example.com",
        },
    )
    draft = generate_draft(client, headers, lead["id"], {"tone": "Professional"})

    delete_response = client.delete(f"/api/v1/email-drafts/{draft['id']}", headers=headers)
    get_response = client.get(f"/api/v1/email-drafts/{draft['id']}", headers=headers)

    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Email draft archived successfully."
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "Archived"

    with testing_session_local() as db:
        activity = db.scalar(
            select(LeadActivity).where(
                LeadActivity.lead_id == lead["id"], LeadActivity.activity_type == "email_draft_archived"
            )
        )

    assert activity is not None
    assert activity.description == "Email draft archived."


def test_archived_and_exported_email_drafts_cannot_be_changed(
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
    archived_draft = generate_draft(client, headers, lead["id"], {"tone": "Professional"})
    client.delete(f"/api/v1/email-drafts/{archived_draft['id']}", headers=headers)

    archived_update_response = client.patch(
        f"/api/v1/email-drafts/{archived_draft['id']}",
        headers=headers,
        json={"subject": "Should not change"},
    )
    archived_rewrite_response = client.post(
        f"/api/v1/email-drafts/{archived_draft['id']}/rewrite",
        headers=headers,
        json={"tone": "Warm"},
    )

    another_lead = create_lead(
        client,
        headers,
        {
            "first_name": "Jordan",
            "last_name": "Lee",
            "email": "jordan@example.com",
        },
    )
    exported_draft = generate_draft(client, headers, another_lead["id"], {"tone": "Professional"})
    with testing_session_local() as db:
        db_draft = db.scalar(select(EmailDraft).where(EmailDraft.id == exported_draft["id"]))
        assert db_draft is not None
        db_draft.status = "Exported"
        db.commit()

    exported_update_response = client.patch(
        f"/api/v1/email-drafts/{exported_draft['id']}",
        headers=headers,
        json={"subject": "Should not change"},
    )

    assert archived_update_response.status_code == 422
    assert archived_rewrite_response.status_code == 422
    assert exported_update_response.status_code == 422


def test_user_can_manage_only_their_own_email_drafts(
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
    draft = generate_draft(client, owner_headers, lead["id"], {"tone": "Professional"})

    get_response = client.get(f"/api/v1/email-drafts/{draft['id']}", headers=other_headers)
    patch_response = client.patch(
        f"/api/v1/email-drafts/{draft['id']}",
        headers=other_headers,
        json={"subject": "Changed"},
    )
    approve_response = client.patch(f"/api/v1/email-drafts/{draft['id']}/approve", headers=other_headers)
    rewrite_response = client.post(
        f"/api/v1/email-drafts/{draft['id']}/rewrite",
        headers=other_headers,
        json={"tone": "Warm"},
    )
    delete_response = client.delete(f"/api/v1/email-drafts/{draft['id']}", headers=other_headers)

    assert get_response.status_code == 404
    assert patch_response.status_code == 404
    assert approve_response.status_code == 404
    assert rewrite_response.status_code == 404
    assert delete_response.status_code == 404
