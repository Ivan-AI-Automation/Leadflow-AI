from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    dashboard,
    email_drafts,
    exports,
    health,
    import_processing,
    imports,
    leads,
    scoring,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(health.router, tags=["health"])
api_router.include_router(imports.router)
api_router.include_router(import_processing.router)
api_router.include_router(scoring.router)
api_router.include_router(leads.router)
api_router.include_router(email_drafts.router)
api_router.include_router(exports.router)
api_router.include_router(dashboard.router)
