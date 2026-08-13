import re
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

class CreatePRRequest(BaseModel):
    provider_id: Optional[str] = None
    repository_path: Optional[str] = None
    github_repo: Optional[str] = None
    base_branch: str = "main"
    head_branch: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    files_to_commit: Optional[List[str]] = None

    @field_validator("github_repo")
    def validate_github_repo(cls, v):
        if not v:
            return v
        v = v.strip().rstrip("/")
        if "github.com/" in v:
            v = v.split("github.com/")[-1]
        parts = v.split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError("github_repo must be in 'owner/repo' format")
        owner, repo = parts[0], parts[1]
        pattern = re.compile(r"^[a-zA-Z0-9_.-]+$")
        if not pattern.match(owner) or not pattern.match(repo):
            raise ValueError("Invalid owner or repository name")
        return f"{owner}/{repo}"

class PullRequestResult(BaseModel):
    success: bool
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    repository: Optional[str] = None
    head_branch: Optional[str] = None
    base_branch: Optional[str] = None
    commit_sha: Optional[str] = None
    title: Optional[str] = None
    status: str
    message: str

class CreateBranchCommitRequest(BaseModel):
    provider_id: Optional[str] = None
    repository_path: Optional[str] = None
    github_repo: Optional[str] = None
    base_branch: str = "main"
    commit_message: Optional[str] = None
    files_to_commit: Optional[List[str]] = None

class CommitResult(BaseModel):
    success: bool
    status: str
    repository: Optional[str] = None
    base_branch: Optional[str] = None
    head_branch: Optional[str] = None
    commit_sha: Optional[str] = None
    files_committed: List[str] = Field(default_factory=list)
    message: str

class AcquireRepoRequest(BaseModel):
    github_repo: str
    base_branch: str = "main"

    @field_validator("github_repo")
    def validate_github_repo(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("github_repo is required")
        v = v.strip().rstrip("/")
        if "github.com/" in v:
            v = v.split("github.com/")[-1]
        parts = v.split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError("github_repo must be in 'owner/repo' format")
        owner, repo = parts[0], parts[1]
        pattern = re.compile(r"^[a-zA-Z0-9_.-]+$")
        if not pattern.match(owner) or not pattern.match(repo):
            raise ValueError("Invalid owner or repository name")
        return f"{owner}/{repo}"

    @field_validator("base_branch")
    def validate_base_branch(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("base_branch is required")
        v = v.strip()
        pattern = re.compile(r"^[a-zA-Z0-9_/.-]+$")
        if not pattern.match(v) or ".." in v or v.startswith("/") or v.endswith("/"):
            raise ValueError("Invalid base branch format")
        return v

class AcquisitionResult(BaseModel):
    success: bool
    workspace_path: Optional[str] = None
    repository: Optional[str] = None
    base_branch: Optional[str] = None
    status: str
    message: str

class CleanupWorkspaceRequest(BaseModel):
    workspace_path: str
