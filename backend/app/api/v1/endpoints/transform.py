from fastapi import APIRouter, Body
from app.models.transformation_result import TransformRequest, TransformationResult
from app.services.code_transformer import apply_transform

router = APIRouter()

@router.post("/transform", response_model=TransformationResult)
async def execute_transform(request: TransformRequest = Body(...)) -> TransformationResult:
    """
    Execute a code transformation deterministically based on a MigrationPlan.
    Defaults to dry_run=True.
    """
    return apply_transform(request.migration_plan, request.repository_root, request.dry_run)
