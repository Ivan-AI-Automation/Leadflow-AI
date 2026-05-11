from __future__ import annotations

from typing import Any

from app.services.api_client import api_client


def list_leads(
    *,
    status: str | None = None,
    category: str | None = None,
    source: str | None = None,
    industry: str | None = None,
    location: str | None = None,
    min_score: int | None = None,
    max_score: int | None = None,
    search: str | None = None,
    missing_email: bool | None = None,
    missing_phone: bool | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict[str, Any]:
    return api_client.get(
        "/api/v1/leads",
        params={
            "status": status,
            "category": category,
            "source": source,
            "industry": industry,
            "location": location,
            "min_score": min_score,
            "max_score": max_score,
            "search": search,
            "missing_email": missing_email,
            "missing_phone": missing_phone,
            "limit": limit,
            "offset": offset,
            "sort_by": sort_by,
            "sort_order": sort_order,
        },
    )


def create_lead(lead_data: dict[str, Any]) -> dict[str, Any]:
    return api_client.post("/api/v1/leads", json=lead_data)


def get_lead(lead_id: int) -> dict[str, Any]:
    return api_client.get(f"/api/v1/leads/{lead_id}")


def update_lead(lead_id: int, lead_data: dict[str, Any]) -> dict[str, Any]:
    return api_client.patch(f"/api/v1/leads/{lead_id}", json=lead_data)


def update_lead_status(lead_id: int, status: str) -> dict[str, Any]:
    return api_client.patch(
        f"/api/v1/leads/{lead_id}/status",
        json={"status": status},
    )


def delete_lead(lead_id: int) -> dict[str, Any]:
    return api_client.delete(f"/api/v1/leads/{lead_id}")


def list_lead_activities(lead_id: int, *, limit: int = 50) -> list[dict[str, Any]]:
    return api_client.get(
        f"/api/v1/leads/{lead_id}/activities",
        params={"limit": limit},
    )
