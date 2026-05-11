from __future__ import annotations

from typing import Any

from app.services.api_client import DownloadedFile, api_client


def export_email_drafts_csv(
    *,
    draft_ids: list[int] | None = None,
    include_draft_status: bool = False,
) -> dict[str, Any]:
    return api_client.post(
        "/api/v1/exports/email-drafts/csv",
        json={
            "draft_ids": draft_ids,
            "include_draft_status": include_draft_status,
        },
    )


def export_email_drafts_excel(
    *,
    draft_ids: list[int] | None = None,
    include_draft_status: bool = False,
) -> dict[str, Any]:
    return api_client.post(
        "/api/v1/exports/email-drafts/excel",
        json={
            "draft_ids": draft_ids,
            "include_draft_status": include_draft_status,
        },
    )


def list_exports(*, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    return api_client.get(
        "/api/v1/exports",
        params={
            "limit": limit,
            "offset": offset,
        },
    )


def download_export(export_id: int) -> DownloadedFile:
    return api_client.download(f"/api/v1/exports/{export_id}/download")
