from fastapi import APIRouter

from app.api.v1.endpoints import diff, migration, transform, providers

router = APIRouter()

router.include_router(diff.router, prefix="/diff", tags=["diff"])
router.include_router(migration.router, prefix="/migration-plan", tags=["migration-plan"])
router.include_router(transform.router, prefix="/transform", tags=["transform"])
router.include_router(providers.router, prefix="/providers", tags=["providers"])