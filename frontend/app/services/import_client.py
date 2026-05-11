from __future__ import annotations

from typing import Any, BinaryIO

from app.services.api_client import api_client, make_upload_file


def upload_import(
    file: BinaryIO,
    *,
    filename: str | None = None,
    content_type: str | None = None,
) -> dict[str, Any]:
    upload_filename = filename or str(getattr(file, "name", "lead_import"))
    upload_content_type = content_type or getattr(file, "type", None)
    files = {
        "file": make_upload_file(file, filename=upload_filename, content_type=upload_content_type),
    }
    return api_client.post("/api/v1/imports/upload", files=files)


def list_imports() -> list[dict[str, Any]]:
    return api_client.get("/api/v1/imports")


def get_import(import_id: int) -> dict[str, Any]:
    return api_client.get(f"/api/v1/imports/{import_id}")


def process_import(import_id: int) -> dict[str, Any]:
    return api_client.post(f"/api/v1/imports/{import_id}/process")


def delete_import(import_id: int) -> dict[str, Any]:
    return api_client.delete(f"/api/v1/imports/{import_id}")
