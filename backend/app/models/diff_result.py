from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ChangeSeverity(str, Enum):
    BREAKING = "BREAKING"
    WARNING = "WARNING"
    INFO = "INFO"

class ChangeType(str, Enum):
    field_removed = "field_removed"
    field_added = "field_added"
    probable_rename = "probable_rename"
    endpoint_removed = "endpoint_removed"
    endpoint_added = "endpoint_added"
    method_removed = "method_removed"
    method_added = "method_added"
    response_removed = "response_removed"
    parameter_removed = "parameter_removed"
    parameter_added = "parameter_added"
    required_parameter_added = "required_parameter_added"
    parameter_type_changed = "parameter_type_changed"
    required_field_added = "required_field_added"
    required_status_changed = "required_status_changed"
    schema_changed = "schema_changed"
    type_changed = "type_changed"

class Change(BaseModel):
    type: ChangeType
    severity: ChangeSeverity
    path: str
    description: str
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DiffResult(BaseModel):
    changes: List[Change] = Field(default_factory=list)
