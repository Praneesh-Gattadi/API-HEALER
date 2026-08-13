from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class MigrationActionType(str, Enum):
    rename_field = "rename_field"
    remove_field = "remove_field"
    add_required_field = "add_required_field"
    update_parameter = "update_parameter"
    update_endpoint = "update_endpoint"
    update_response_handling = "update_response_handling"
    update_request_handling = "update_request_handling"
    review_required = "review_required"

class MigrationAction(BaseModel):
    action_type: MigrationActionType
    description: str = Field(description="Human-readable description of the action.")
    old_name: Optional[str] = Field(None, description="The old name of the field, parameter, or endpoint, if applicable.")
    new_name: Optional[str] = Field(None, description="The new name of the field, parameter, or endpoint, if applicable.")
    affected_path: str = Field(description="The API path or specific location affected (e.g., /users.GET).")
    confidence: Optional[float] = Field(None, description="Confidence score between 0.0 and 1.0, if applicable.")
    rationale: str = Field(description="The reasoning behind why this action is necessary.")
    validation_required: str = Field(description="What needs to be validated or updated by the developer after this action.")

class MigrationPlan(BaseModel):
    summary: str = Field(description="A high-level summary of the migration plan.")
    risk_level: str = Field(description="The overall risk level of the migration (e.g., LOW, MEDIUM, HIGH).")
    actions: List[MigrationAction] = Field(description="The list of specific migration actions required.", default_factory=list)
    affected_files: List[str] = Field(description="List of consumer files affected by these changes.", default_factory=list)
    validation_steps: List[str] = Field(description="High-level steps required to validate the entire migration.", default_factory=list)
