from fastapi import APIRouter

from app.api.v1.endpoints import diff

router = APIRouter()

router.include_router(diff.router, tags=["diff"])