from typing import Any, Dict
from fastapi import APIRouter, Body
from pydantic import BaseModel

from app.models.diff_result import DiffResult
from app.services.openapi_diff import compare_openapi_specs

router = APIRouter()

class DiffRequest(BaseModel):
    old_spec: Dict[str, Any]
    new_spec: Dict[str, Any]

@router.post("/diff", response_model=DiffResult)
async def calculate_diff(request: DiffRequest = Body(...)) -> DiffResult:
    """
    Compare two OpenAPI specifications and return a deterministic list of changes.
    """
    return compare_openapi_specs(request.old_spec, request.new_spec)
