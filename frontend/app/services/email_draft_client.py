from __future__ import annotations

from typing import Any

from app.services.api_client import api_client


def generate_email_draft(
    lead_id: int,
    *,
    tone: str = "Professional",
    business_type: str | None = None,
    sender_company_name: str | None = None,
    overwrite_existing: bool = False,
) -> dict[str, Any]:
    return api_client.post(
        f"/api/v1/leads/{lead_id}/email-draft",
        json={
            "tone": tone,
            "business_type": business_type,
            "sender_company_name": sender_company_name,
            "overwrite_existing": overwrite_existing,
        },
    )


def generate_bulk_email_drafts(
    lead_ids: list[int],
    *,
    tone: str = "Professional",
    business_type: str | None = None,
    sender_company_name: str | None = None,
    overwrite_existing: bool = False,
) -> dict[str, Any]:
    return api_client.post(
        "/api/v1/email-drafts/bulk",
        json={
            "lead_ids": lead_ids,
            "tone": tone,
            "business_type": business_type,
            "sender_company_name": sender_company_name,
            "overwrite_existing": overwrite_existing,
        },
    )


def list_email_drafts(
    *,
    status: str | None = None,
    tone: str | None = None,
    lead_category: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_order: str = "desc",
) -> dict[str, Any]:
    return api_client.get(
        "/api/v1/email-drafts",
        params={
            "status": status,
            "tone": tone,
            "lead_category": lead_category,
            "search": search,
            "limit": limit,
            "offset": offset,
            "sort_by": "created_at",
            "sort_order": sort_order,
        },
    )


def get_email_draft(draft_id: int) -> dict[str, Any]:
    return api_client.get(f"/api/v1/email-drafts/{draft_id}")


def update_email_draft(draft_id: int, draft_data: dict[str, Any]) -> dict[str, Any]:
    return api_client.patch(f"/api/v1/email-drafts/{draft_id}", json=draft_data)


def approve_email_draft(draft_id: int) -> dict[str, Any]:
    return api_client.patch(f"/api/v1/email-drafts/{draft_id}/approve")


def rewrite_email_draft(
    draft_id: int,
    *,
    tone: str = "Professional",
    business_type: str | None = None,
    sender_company_name: str | None = None,
) -> dict[str, Any]:
    return api_client.post(
        f"/api/v1/email-drafts/{draft_id}/rewrite",
        json={
            "tone": tone,
            "business_type": business_type,
            "sender_company_name": sender_company_name,
        },
    )


def archive_email_draft(draft_id: int) -> dict[str, Any]:
    return api_client.delete(f"/api/v1/email-drafts/{draft_id}")
