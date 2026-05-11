from __future__ import annotations

import csv
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.email_draft import EmailDraft
from app.models.exported_email_batch import ExportedEmailBatch
from app.models.lead_activity import LeadActivity
import app.models as _models  # noqa: F401


@pytest.fixture()
def client_and_session(tmp_path: Path) -> Generator[tuple[TestClient, sessionmaker[Session], Path], None, None]:
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
    original_ai_provider = settings.ai_provider
    settings.upload_dir = tmp_path / "uploads"
    settings.export_dir = tmp_path / "exports"
    settings.ai_provider = "mock"

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client, testing_session_local, settings.export_dir

    app.dependency_overrides.clear()
    settings.upload_dir = original_upload_dir
    settings.export_dir = original_export_dir
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


def generate_draft(client: TestClient, headers: dict[str, str], lead_id: int) -> dict[str, object]:
    response = client.post(
        f"/api/v1/leads/{lead_id}/email-draft",
        headers=headers,
        json={
            "tone": "Professional",
            "sender_company_name": "LeadFlow AI",
        },
    )
    assert response.status_code == 201
    return response.json()


def approve_draft(client: TestClient, headers: dict[str, str], draft_id: int) -> dict[str, object]:
    response = client.patch(f"/api/v1/email-drafts/{draft_id}/approve", headers=headers)
    assert response.status_code == 200
    return response.json()


def test_csv_export_includes_approved_drafts_by_default_and_marks_them_exported(
    client_and_session: tuple[TestClient, sessionmaker[Session], Path],
) -> None:
    client, testing_session_local, _ = client_and_session
    headers = auth_header(client)
    approved_lead = create_lead(
        client,
        headers,
        {
            "first_name": "Maya",
            "last_name": "Patel",
            "company_name": "Northstar Homes",
            "email": "maya@example.com",
        },
    )
    draft_lead = create_lead(
        client,
        headers,
        {
            "first_name": "Jordan",
            "last_name": "Lee",
            "company_name": "BrightPath Marketing",
            "email": "jordan@example.com",
        },
    )
    client.patch(
        f"/api/v1/leads/{approved_lead['id']}", headers=headers, json={"category": "Hot", "priority_score": 91}
    )
    client.patch(f"/api/v1/leads/{draft_lead['id']}", headers=headers, json={"category": "Warm", "priority_score": 68})
    approved_draft = approve_draft(client, headers, generate_draft(client, headers, approved_lead["id"])["id"])
    draft_status_draft = generate_draft(client, headers, draft_lead["id"])

    response = client.post("/api/v1/exports/email-drafts/csv", headers=headers, json={})

    assert response.status_code == 201
    payload = response.json()
    assert payload["format"] == "csv"
    assert payload["lead_count"] == 1

    export_path = Path(payload["file_path"])
    assert export_path.exists()
    with export_path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 1
    assert rows[0]["lead_id"] == str(approved_lead["id"])
    assert rows[0]["first_name"] == "Maya"
    assert rows[0]["company_name"] == "Northstar Homes"
    assert rows[0]["email"] == "maya@example.com"
    assert rows[0]["category"] == "Hot"
    assert rows[0]["priority_score"] == "91"
    assert rows[0]["email_subject"] == approved_draft["subject"]
    assert rows[0]["draft_status"] == "Approved"

    with testing_session_local() as db:
        exported_draft = db.get(EmailDraft, approved_draft["id"])
        untouched_draft = db.get(EmailDraft, draft_status_draft["id"])
        batch = db.scalar(select(ExportedEmailBatch).where(ExportedEmailBatch.id == payload["id"]))
        activity = db.scalar(
            select(LeadActivity).where(
                LeadActivity.lead_id == approved_lead["id"],
                LeadActivity.activity_type == "email_draft_exported",
            )
        )

    assert exported_draft is not None
    assert exported_draft.status == "Exported"
    assert untouched_draft is not None
    assert untouched_draft.status == "Draft"
    assert batch is not None
    assert batch.lead_count == 1
    assert activity is not None
    assert activity.description == "Email draft exported from Approved status."


def test_excel_export_can_include_draft_status_emails(
    client_and_session: tuple[TestClient, sessionmaker[Session], Path],
) -> None:
    client, testing_session_local, _ = client_and_session
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
    client.patch(f"/api/v1/leads/{lead['id']}", headers=headers, json={"category": "Warm", "priority_score": 72})
    draft = generate_draft(client, headers, lead["id"])

    response = client.post(
        "/api/v1/exports/email-drafts/excel",
        headers=headers,
        json={
            "draft_ids": [draft["id"]],
            "include_draft_status": True,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["format"] == "xlsx"
    assert payload["lead_count"] == 1

    workbook = load_workbook(payload["file_path"])
    worksheet = workbook["Email Drafts"]
    headers_row = [cell.value for cell in worksheet[1]]
    values_row = [cell.value for cell in worksheet[2]]

    assert headers_row == [
        "lead_id",
        "first_name",
        "last_name",
        "company_name",
        "email",
        "status",
        "category",
        "priority_score",
        "email_subject",
        "email_body",
        "draft_status",
    ]
    assert values_row[0] == lead["id"]
    assert values_row[1] == "Avery"
    assert values_row[4] == "avery@example.com"
    assert values_row[10] == "Draft"
    assert worksheet.freeze_panes == "A2"
    assert worksheet.column_dimensions["I"].width >= 36
    assert worksheet.column_dimensions["J"].width >= 60

    with testing_session_local() as db:
        exported_draft = db.get(EmailDraft, draft["id"])

    assert exported_draft is not None
    assert exported_draft.status == "Exported"


def test_export_returns_validation_error_when_no_approved_drafts_exist(
    client_and_session: tuple[TestClient, sessionmaker[Session], Path],
) -> None:
    client, _testing_session_local, _ = client_and_session
    headers = auth_header(client)
    lead = create_lead(
        client,
        headers,
        {
            "first_name": "Liam",
            "last_name": "Owen",
            "email": "liam@example.com",
        },
    )
    generate_draft(client, headers, lead["id"])

    response = client.post("/api/v1/exports/email-drafts/csv", headers=headers, json={})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["message"] == "No approved email drafts are available to export."


def test_list_exports_and_download_are_scoped_to_current_user(
    client_and_session: tuple[TestClient, sessionmaker[Session], Path],
) -> None:
    client, _testing_session_local, _ = client_and_session
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
    draft = generate_draft(client, owner_headers, lead["id"])
    approve_draft(client, owner_headers, draft["id"])
    export_response = client.post("/api/v1/exports/email-drafts/csv", headers=owner_headers, json={})
    export_id = export_response.json()["id"]

    owner_list_response = client.get("/api/v1/exports", headers=owner_headers)
    other_list_response = client.get("/api/v1/exports", headers=other_headers)
    owner_download_response = client.get(f"/api/v1/exports/{export_id}/download", headers=owner_headers)
    other_download_response = client.get(f"/api/v1/exports/{export_id}/download", headers=other_headers)

    assert owner_list_response.status_code == 200
    assert owner_list_response.json()["meta"]["total"] == 1
    assert owner_list_response.json()["items"][0]["id"] == export_id
    assert other_list_response.status_code == 200
    assert other_list_response.json()["meta"]["total"] == 0
    assert owner_download_response.status_code == 200
    assert owner_download_response.headers["content-type"].startswith("text/csv")
    assert b"maya@example.com" in owner_download_response.content
    assert other_download_response.status_code == 404
