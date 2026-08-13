from fastapi import APIRouter

from app.api.v1.endpoints import diff, migration, transform

router = APIRouter()

router.include_router(diff.router, tags=["diff"])
router.include_router(migration.router, tags=["migration"])
router.include_router(transform.router, tags=["transform"])