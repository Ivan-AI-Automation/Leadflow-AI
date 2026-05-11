from __future__ import annotations

from typing import Any

from app.services.api_client import api_client


def score_lead(lead_id: int) -> dict[str, Any]:
    return api_client.post(f"/api/v1/leads/{lead_id}/score")


def get_lead_score(lead_id: int) -> dict[str, Any]:
    return api_client.get(f"/api/v1/leads/{lead_id}/score")


def score_import(import_id: int) -> dict[str, Any]:
    return api_client.post(f"/api/v1/imports/{import_id}/score")


def score_all_leads() -> dict[str, Any]:
    return api_client.post("/api/v1/leads/score-all")
