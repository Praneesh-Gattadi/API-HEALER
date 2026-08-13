from typing import Any, Dict
from fastapi import APIRouter, Body
from pydantic import BaseModel

from app.models.migration_plan import MigrationPlan
from app.services.openapi_diff import compare_openapi_specs
from app.services.migration_planner import generate_migration_plan

router = APIRouter()

class MigrationRequest(BaseModel):
    old_spec: Dict[str, Any]
    new_spec: Dict[str, Any]

@router.post("/migration-plan", response_model=MigrationPlan)
async def create_migration_plan(request: MigrationRequest = Body(...)) -> MigrationPlan:
    """
    Compare two OpenAPI specs and generate an actionable migration plan.
    """
    diff_result = compare_openapi_specs(request.old_spec, request.new_spec)
    return await generate_migration_plan(diff_result, request.old_spec, request.new_spec)
