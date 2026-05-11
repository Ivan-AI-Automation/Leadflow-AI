from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.export import EmailDraftExportRequest, ExportFormat, ExportListResponse, ExportResponse
from app.services.export_service import ExportService

router = APIRouter(prefix="/exports", tags=["exports"])


@router.post("/email-drafts/csv", response_model=ExportResponse, status_code=201)
def export_email_drafts_to_csv(
    request: EmailDraftExportRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ExportResponse:
    export_batch = ExportService.export_email_drafts(
        db,
        current_user=current_user,
        request=request,
        export_format=ExportFormat.CSV,
    )
    return ExportResponse.model_validate(export_batch)


@router.post("/email-drafts/excel", response_model=ExportResponse, status_code=201)
def export_email_drafts_to_excel(
    request: EmailDraftExportRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ExportResponse:
    export_batch = ExportService.export_email_drafts(
        db,
        current_user=current_user,
        request=request,
        export_format=ExportFormat.XLSX,
    )
    return ExportResponse.model_validate(export_batch)


@router.get("", response_model=ExportListResponse)
def list_exports(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ExportListResponse:
    return ExportService.list_exports(
        db,
        current_user=current_user,
        limit=limit,
        offset=offset,
    )


@router.get("/{export_id}/download")
def download_export(
    export_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    export_batch = ExportService.get_export_for_download(
        db,
        current_user=current_user,
        export_id=export_id,
    )
    file_path = Path(export_batch.file_path)
    media_type = (
        "text/csv"
        if export_batch.format == ExportFormat.CSV.value
        else ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    )
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type=media_type,
    )
