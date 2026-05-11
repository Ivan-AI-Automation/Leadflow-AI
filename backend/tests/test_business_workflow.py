from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.models.email_draft import EmailDraft
from app.models.lead import Lead
from app.models.lead_score import LeadScore


def test_shared_fixtures_build_a_realistic_follow_up_workflow(
    client: TestClient,
    auth_headers: dict[str, str],
    test_user: dict[str, object],
    uploaded_import: dict[str, object],
    processed_leads: list[Lead],
    scored_leads: list[Lead],
    saved_lead_scores: list[LeadScore],
    approved_email_draft: EmailDraft,
) -> None:
    assert test_user["email"] == "owner@example.com"
    assert uploaded_import["rows_count"] == 3
    assert len(processed_leads) == 3
    assert any(lead.email is None for lead in processed_leads)
    assert len(scored_leads) == 3
    assert len(saved_lead_scores) == 3
    assert approved_email_draft.status == "Approved"

    summary_response = client.get("/api/v1/dashboard/summary", headers=auth_headers)

    assert summary_response.status_code == 200
    assert summary_response.json()["total_leads"] == 3
    assert summary_response.json()["drafts_approved"] == 1


def test_ready_to_send_exports_from_approved_drafts(
    client: TestClient,
    auth_headers: dict[str, str],
    approved_email_draft: EmailDraft,
    test_db: Session,
) -> None:
    csv_response = client.post("/api/v1/exports/email-drafts/csv", headers=auth_headers, json={})

    assert csv_response.status_code == 201
    csv_payload = csv_response.json()
    assert csv_payload["format"] == "csv"
    assert csv_payload["lead_count"] == 1
    assert Path(csv_payload["file_path"]).exists()

    test_db.expire_all()
    refreshed_draft = test_db.get(EmailDraft, approved_email_draft.id)
    assert refreshed_draft is not None
    assert refreshed_draft.status == "Exported"


def test_excel_export_can_include_draft_status_emails(
    client: TestClient,
    auth_headers: dict[str, str],
    email_draft: EmailDraft,
) -> None:
    response = client.post(
        "/api/v1/exports/email-drafts/excel",
        headers=auth_headers,
        json={
            "draft_ids": [email_draft.id],
            "include_draft_status": True,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["format"] == "xlsx"
    assert payload["lead_count"] == 1

    workbook = load_workbook(payload["file_path"])
    worksheet = workbook["Email Drafts"]
    assert worksheet["A1"].value == "lead_id"
    assert worksheet["J1"].value == "email_body"
    assert worksheet["K2"].value == "Draft"
