from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.migration_plan import MigrationPlan

class FileChange(BaseModel):
    file_path: str = Field(description="The absolute or relative path to the modified file.")
    original_content_hash: str = Field(description="Hash of the original file content.")
    proposed_content_hash: str = Field(description="Hash of the proposed file content.")
    diff: str = Field(description="The unified diff string showing proposed changes.")

class TransformWarning(BaseModel):
    file_path: Optional[str] = None
    line: Optional[int] = None
    message: str

class TransformationResult(BaseModel):
    success: bool = Field(description="True if transformation was successful (including successful dry runs).")
    files_changed: List[str] = Field(default_factory=list, description="List of file paths that were or would be changed.")
    changes: List[FileChange] = Field(default_factory=list, description="Detailed list of file changes.")
    warnings: List[TransformWarning] = Field(default_factory=list, description="Warnings about skipped or unsupported actions.")
    errors: List[str] = Field(default_factory=list, description="Errors that occurred during transformation or validation.")

class TransformRequest(BaseModel):
    migration_plan: MigrationPlan
    repository_root: str
    dry_run: bool = True
