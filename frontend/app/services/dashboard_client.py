from __future__ import annotations

from typing import Any

from app.services.api_client import api_client


def get_dashboard_summary() -> dict[str, Any]:
    return api_client.get("/api/v1/dashboard/summary")


def get_dashboard_charts() -> dict[str, Any]:
    return api_client.get("/api/v1/dashboard/charts")
