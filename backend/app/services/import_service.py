from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pandas as pd
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import FileTooLargeError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.lead_import import LeadImport
from app.models.user import User
from app.repositories.import_repository import (
    create_lead_import,
    delete_lead_import,
    get_lead_import_for_user,
    list_lead_imports_for_user,
)

logger = get_logger(__name__)

ALLOWED_IMPORT_EXTENSIONS = {".csv", ".xlsx", ".xls"}


@dataclass(frozen=True)
class FilePreview:
    rows_count: int
    columns_count: int
    columns_json: list[str]
    dtypes_json: dict[str, str]


def get_safe_original_filename(filename: str | None) -> str:
    original_filename = Path(filename or "").name.strip()
    if not original_filename:
        raise ValidationError("The uploaded file must have a filename.")
    return original_filename


def get_file_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_IMPORT_EXTENSIONS:
        allowed_formats = ", ".join(sorted(ALLOWED_IMPORT_EXTENSIONS))
        raise ValidationError(f"Unsupported file format. Please upload one of these formats: {allowed_formats}.")
    return extension


def generate_stored_filename(extension: str) -> str:
    return f"{uuid4().hex}{extension}"


def validate_file_size(file_bytes: bytes, max_upload_size_mb: int) -> None:
    if not file_bytes:
        raise ValidationError("The uploaded file is empty.")

    max_size_bytes = max_upload_size_mb * 1024 * 1024
    if len(file_bytes) > max_size_bytes:
        raise FileTooLargeError(f"The uploaded file is too large. The maximum allowed size is {max_upload_size_mb} MB.")


def read_file_preview(file_bytes: bytes, file_type: str) -> FilePreview:
    try:
        if file_type == "csv":
            dataframe = pd.read_csv(BytesIO(file_bytes))
        else:
            dataframe = pd.read_excel(BytesIO(file_bytes))
    except Exception as exc:
        raise ValidationError(
            "The uploaded file could not be read. Please check that it is a valid CSV or Excel file."
        ) from exc

    column_names = [str(column) for column in dataframe.columns]
    dtypes = {str(column): str(dtype) for column, dtype in dataframe.dtypes.items()}

    return FilePreview(
        rows_count=len(dataframe),
        columns_count=len(column_names),
        columns_json=column_names,
        dtypes_json=dtypes,
    )


def save_uploaded_file(upload_dir: Path, stored_filename: str, file_bytes: bytes) -> Path:
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / stored_filename
    file_path.write_bytes(file_bytes)
    return file_path


async def upload_lead_import(db: Session, *, current_user: User, file: UploadFile) -> LeadImport:
    settings = get_settings()
    original_filename = get_safe_original_filename(file.filename)
    extension = get_file_extension(original_filename)
    file_type = extension.removeprefix(".")
    stored_filename = generate_stored_filename(extension)

    file_bytes = await file.read()
    validate_file_size(file_bytes, settings.max_upload_size_mb)
    preview = read_file_preview(file_bytes, file_type)

    saved_file_path = save_uploaded_file(settings.upload_dir, stored_filename, file_bytes)

    logger.info(
        "User %s uploaded lead import %s as %s",
        current_user.id,
        original_filename,
        saved_file_path,
    )

    return create_lead_import(
        db,
        user_id=current_user.id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_type=file_type,
        rows_count=preview.rows_count,
        columns_count=preview.columns_count,
        columns_json=preview.columns_json,
        dtypes_json=preview.dtypes_json,
        status="uploaded",
    )


def list_imports(db: Session, *, current_user: User) -> list[LeadImport]:
    return list_lead_imports_for_user(db, user_id=current_user.id)


def get_import(db: Session, *, current_user: User, import_id: int) -> LeadImport:
    lead_import = get_lead_import_for_user(db, import_id=import_id, user_id=current_user.id)
    if lead_import is None:
        raise NotFoundError("The requested import was not found.")
    return lead_import


def delete_import(db: Session, *, current_user: User, import_id: int) -> None:
    settings = get_settings()
    lead_import = get_import(db, current_user=current_user, import_id=import_id)
    file_path = settings.upload_dir / lead_import.stored_filename

    if file_path.exists():
        file_path.unlink()

    delete_lead_import(db, lead_import)
    logger.info("User %s deleted lead import %s", current_user.id, import_id)
