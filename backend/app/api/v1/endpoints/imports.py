from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.lead_import import LeadImportResponse
from app.services.import_service import delete_import, get_import, list_imports, upload_lead_import

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/upload", response_model=LeadImportResponse, status_code=status.HTTP_201_CREATED)
async def upload_import(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(description="CSV or Excel file containing lead data.")],
) -> LeadImportResponse:
    lead_import = await upload_lead_import(db, current_user=current_user, file=file)
    return LeadImportResponse.model_validate(lead_import)


@router.get("", response_model=list[LeadImportResponse])
def get_imports(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[LeadImportResponse]:
    imports = list_imports(db, current_user=current_user)
    return [LeadImportResponse.model_validate(lead_import) for lead_import in imports]


@router.get("/{import_id}", response_model=LeadImportResponse)
def get_import_by_id(
    import_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> LeadImportResponse:
    lead_import = get_import(db, current_user=current_user, import_id=import_id)
    return LeadImportResponse.model_validate(lead_import)


@router.delete("/{import_id}", response_model=MessageResponse)
def delete_import_by_id(
    import_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    delete_import(db, current_user=current_user, import_id=import_id)
    return MessageResponse(message="Lead import deleted successfully.")
