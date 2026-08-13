import os
import glob
from fastapi import APIRouter, HTTPException
from app.models.github import CreatePRRequest, PullRequestResult, AcquireRepoRequest, AcquisitionResult, CleanupWorkspaceRequest, CreateBranchCommitRequest, CommitResult
from app.services.github_service import GitHubService
from app.services.provider_store import ProviderStore

router = APIRouter()

UNSAFE_PATTERNS = [".env", ".git", "key", "secret", "credential", "token", ".."]

def is_safe_file_path(repo_root_abs: str, file_path_abs: str) -> bool:
    try:
        common = os.path.commonpath([repo_root_abs, file_path_abs])
        if os.path.abspath(common) != repo_root_abs:
            return False

        rel_path = os.path.relpath(file_path_abs, repo_root_abs).replace("\\", "/")
        parts = rel_path.split("/")

        for part in parts:
            part_lower = part.lower()
            for pattern in UNSAFE_PATTERNS:
                if pattern in part_lower and pattern != "..":
                    return False
        return True
    except Exception:
        return False

@router.post("/acquire-repo", response_model=AcquisitionResult)
async def acquire_repository(req: AcquireRepoRequest):
    github_service = GitHubService()
    result = await github_service.acquire_repository(
        github_repo=req.github_repo,
        base_branch=req.base_branch
    )
    return result

@router.post("/cleanup-workspace")
async def cleanup_workspace(req: CleanupWorkspaceRequest):
    success = GitHubService.cleanup_workspace(req.workspace_path)
    if not success:
        return {"success": False, "message": "Failed to cleanup workspace or path failed security checks."}
    return {"success": True, "message": "Workspace cleaned up successfully."}

@router.post("/commit", response_model=CommitResult)
async def create_branch_and_commit(req: CreateBranchCommitRequest):
    github_service = GitHubService()

    if not github_service.is_configured():
        return CommitResult(
            success=False,
            status="NOT_CONFIGURED",
            message="GitHub integration is not configured. Server GITHUB_TOKEN environment variable is missing."
        )

    # 1. Resolve Provider and Repository info
    github_repo = req.github_repo
    repo_path = req.repository_path

    if req.provider_id:
        store = ProviderStore()
        provider = store.get_provider(req.provider_id)
        if provider:
            if not github_repo and provider.github_repo:
                github_repo = provider.github_repo
            if not repo_path:
                repo_path = provider.workspace_path or provider.repository_path

    if not github_repo:
        return CommitResult(
            success=False,
            status="MISSING_GITHUB_REPO",
            message="GitHub repository ('owner/repo') must be provided in request or registered with provider."
        )

    if not repo_path:
        return CommitResult(
            success=False,
            status="MISSING_REPOSITORY_PATH",
            message="Local or acquired workspace repository path must be provided in request or registered with provider."
        )

    abs_repo = os.path.abspath(repo_path)
    if not os.path.exists(abs_repo) or not os.path.isdir(abs_repo):
        return CommitResult(
            success=False,
            status="INVALID_REPOSITORY_PATH",
            message=f"Configured repository path '{repo_path}' does not exist or is not a directory."
        )

    # 2. Collect files to commit safely
    files_map = {}

    if req.files_to_commit and len(req.files_to_commit) > 0:
        target_files = req.files_to_commit
    else:
        target_files = glob.glob(os.path.join(abs_repo, "**", "*.py"), recursive=True)

    for target in target_files:
        abs_target = os.path.abspath(target if os.path.isabs(target) else os.path.join(abs_repo, target))

        if not os.path.isfile(abs_target):
            continue

        if not is_safe_file_path(abs_repo, abs_target):
            return CommitResult(
                success=False,
                status="UNSAFE_FILE_PATH",
                message=f"File path '{target}' failed security checks (path traversal or sensitive file)."
            )

        rel_path = os.path.relpath(abs_target, abs_repo).replace("\\", "/")
        try:
            with open(abs_target, "r", encoding="utf-8") as f:
                files_map[rel_path] = f.read()
        except Exception as e:
            return CommitResult(
                success=False,
                status="FILE_READ_ERROR",
                message=f"Failed to read local file '{rel_path}': {str(e)}"
            )

    if not files_map:
        return CommitResult(
            success=False,
            status="NO_CHANGES",
            message="No valid Python files found in repository to commit."
        )

    result = await github_service.create_branch_and_commit(
        github_repo=github_repo,
        files_map=files_map,
        base_branch=req.base_branch or "main",
        commit_message=req.commit_message
    )

    return result

@router.post("/pull-request", response_model=PullRequestResult)
async def create_pull_request(req: CreatePRRequest):
    github_service = GitHubService()

    if not github_service.is_configured():
        return PullRequestResult(
            success=False,
            status="NOT_CONFIGURED",
            message="GitHub integration is not configured. Server GITHUB_TOKEN environment variable is missing."
        )

    # 1. Resolve Provider and Repository info
    github_repo = req.github_repo
    repo_path = req.repository_path

    if req.provider_id:
        store = ProviderStore()
        provider = store.get_provider(req.provider_id)
        if provider:
            if not github_repo and provider.github_repo:
                github_repo = provider.github_repo
            if not repo_path and provider.repository_path:
                repo_path = provider.repository_path

    if not github_repo:
        return PullRequestResult(
            success=False,
            status="MISSING_GITHUB_REPO",
            message="GitHub repository ('owner/repo') must be provided in request or registered with provider."
        )

    if not repo_path:
        return PullRequestResult(
            success=False,
            status="MISSING_REPOSITORY_PATH",
            message="Local repository path must be provided in request or registered with provider."
        )

    abs_repo = os.path.abspath(repo_path)
    if not os.path.exists(abs_repo) or not os.path.isdir(abs_repo):
        return PullRequestResult(
            success=False,
            status="INVALID_REPOSITORY_PATH",
            message=f"Configured repository path '{repo_path}' does not exist or is not a directory."
        )

    # 2. Collect files to commit safely
    files_map = {}

    if req.files_to_commit and len(req.files_to_commit) > 0:
        target_files = req.files_to_commit
    else:
        target_files = glob.glob(os.path.join(abs_repo, "**", "*.py"), recursive=True)

    for target in target_files:
        abs_target = os.path.abspath(target if os.path.isabs(target) else os.path.join(abs_repo, target))

        if not os.path.isfile(abs_target):
            continue

        if not is_safe_file_path(abs_repo, abs_target):
            return PullRequestResult(
                success=False,
                status="UNSAFE_FILE_PATH",
                message=f"File path '{target}' failed security checks (path traversal or sensitive file)."
            )

        rel_path = os.path.relpath(abs_target, abs_repo).replace("\\", "/")
        try:
            with open(abs_target, "r", encoding="utf-8") as f:
                files_map[rel_path] = f.read()
        except Exception as e:
            return PullRequestResult(
                success=False,
                status="FILE_READ_ERROR",
                message=f"Failed to read local file '{rel_path}': {str(e)}"
            )

    if not files_map:
        return PullRequestResult(
            success=False,
            status="NO_FILES_TO_COMMIT",
            message="No valid Python files found in consumer repository to commit."
        )

    result = await github_service.create_pull_request(
        github_repo=github_repo,
        files_map=files_map,
        base_branch=req.base_branch or "main",
        title=req.title,
        body=req.body
    )

    return result
