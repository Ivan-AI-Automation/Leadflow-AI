from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.lead_import import LeadImportProcessResponse
from app.services.lead_import_processor import LeadImportProcessor

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/{import_id}/process", response_model=LeadImportProcessResponse)
def process_import(
    import_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> LeadImportProcessResponse:
    return LeadImportProcessor.process_import(
        db,
        current_user=current_user,
        import_id=import_id,
    )
