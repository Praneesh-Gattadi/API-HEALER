import os
import io
import re
import base64
import uuid
import shutil
import tempfile
import zipfile
import httpx
from typing import Dict, Any, Optional, Tuple
from app.models.github import PullRequestResult, AcquisitionResult, CommitResult

class GitHubService:
    BASE_URL = "https://api.github.com"
    TIMEOUT = 15.0

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN", "").strip()

    def is_configured(self) -> bool:
        return bool(self.token)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "API-Healer-Bot"
        }

    @staticmethod
    def _is_safe_zip_entry(workspace_dir: str, filename: str) -> Tuple[bool, str]:
        if not filename:
            return False, ""

        norm_name = filename.replace("\\", "/")
        if norm_name.startswith("/") or re.match(r"^[a-zA-Z]:", norm_name):
            return False, ""

        if ".." in norm_name.split("/"):
            return False, ""

        try:
            abs_workspace = os.path.realpath(os.path.abspath(workspace_dir))
            target_path = os.path.realpath(os.path.abspath(os.path.join(workspace_dir, norm_name)))

            common = os.path.commonpath([abs_workspace, target_path])
            if common != abs_workspace:
                return False, ""
            return True, target_path
        except Exception:
            return False, ""

    @staticmethod
    def cleanup_workspace(workspace_path: str) -> bool:
        if not workspace_path or not isinstance(workspace_path, str):
            return False

        try:
            abs_ws = os.path.realpath(os.path.abspath(workspace_path))
            system_temp = os.path.realpath(os.path.abspath(tempfile.gettempdir()))

            if not os.path.exists(abs_ws) or not os.path.isdir(abs_ws):
                return False

            if not abs_ws.startswith(system_temp) or abs_ws == system_temp:
                return False

            base = os.path.basename(abs_ws)
            if not base.startswith("api_healer_workspace_"):
                return False

            repo_root = os.path.realpath(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
            user_home = os.path.realpath(os.path.expanduser("~"))

            if abs_ws == repo_root or repo_root.startswith(abs_ws) or abs_ws.startswith(repo_root):
                return False

            if abs_ws == user_home or user_home.startswith(abs_ws):
                return False

            shutil.rmtree(abs_ws, ignore_errors=True)
            return not os.path.exists(abs_ws)
        except Exception:
            return False

    async def acquire_repository(
        self,
        github_repo: str,
        base_branch: str = "main"
    ) -> AcquisitionResult:
        if not self.is_configured():
            return AcquisitionResult(
                success=False,
                status="NOT_CONFIGURED",
                message="GitHub integration is not configured. Server GITHUB_TOKEN environment variable is missing."
            )

        if not github_repo or "/" not in github_repo:
            return AcquisitionResult(
                success=False,
                status="INVALID_REPOSITORY",
                message=f"Invalid GitHub repository specification: '{github_repo}'"
            )

        parts = github_repo.strip().rstrip("/").split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return AcquisitionResult(
                success=False,
                status="INVALID_REPOSITORY",
                message=f"Invalid GitHub repository format: '{github_repo}'"
            )

        owner, repo = parts[0], parts[1]

        pattern = re.compile(r"^[a-zA-Z0-9_.-]+$")
        if not pattern.match(owner) or not pattern.match(repo):
            return AcquisitionResult(
                success=False,
                status="INVALID_REPOSITORY",
                message="Invalid characters in GitHub owner or repository name."
            )

        branch_pattern = re.compile(r"^[a-zA-Z0-9_/.-]+$")
        if not base_branch or not branch_pattern.match(base_branch) or ".." in base_branch:
            return AcquisitionResult(
                success=False,
                status="INVALID_BRANCH",
                message=f"Invalid base branch specification: '{base_branch}'"
            )

        async with httpx.AsyncClient(timeout=self.TIMEOUT, follow_redirects=True) as client:
            try:
                repo_resp = await client.get(
                    f"{self.BASE_URL}/repos/{owner}/{repo}",
                    headers=self._headers()
                )
                if repo_resp.status_code == 404:
                    return AcquisitionResult(
                        success=False,
                        status="REPOSITORY_NOT_FOUND",
                        message=f"Repository '{owner}/{repo}' not found on GitHub."
                    )
                elif repo_resp.status_code == 403:
                    return AcquisitionResult(
                        success=False,
                        status="PERMISSION_DENIED",
                        message="GitHub API access denied (403). Check GITHUB_TOKEN permissions."
                    )
                repo_resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                return AcquisitionResult(
                    success=False,
                    status=f"HTTP_{e.response.status_code}",
                    message=f"GitHub API error ({e.response.status_code}) inspecting repository."
                )
            except httpx.HTTPError as e:
                return AcquisitionResult(
                    success=False,
                    status="GITHUB_NETWORK_ERROR",
                    message=f"Network error communicating with GitHub: {str(e)}"
                )

            try:
                ref_resp = await client.get(
                    f"{self.BASE_URL}/repos/{owner}/{repo}/git/ref/heads/{base_branch}",
                    headers=self._headers()
                )
                if ref_resp.status_code == 404:
                    return AcquisitionResult(
                        success=False,
                        status="BRANCH_NOT_FOUND",
                        message=f"Base branch '{base_branch}' not found in repository '{owner}/{repo}'."
                    )
                ref_resp.raise_for_status()
            except httpx.HTTPError as e:
                return AcquisitionResult(
                    success=False,
                    status="BRANCH_CHECK_FAILED",
                    message=f"Failed to verify branch '{base_branch}': {str(e)}"
                )

            workspace_dir = tempfile.mkdtemp(prefix="api_healer_workspace_")
            abs_workspace = os.path.realpath(os.path.abspath(workspace_dir))

            system_temp = os.path.realpath(os.path.abspath(tempfile.gettempdir()))
            repo_root = os.path.realpath(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

            if not abs_workspace.startswith(system_temp) or abs_workspace == repo_root or repo_root.startswith(abs_workspace):
                shutil.rmtree(workspace_dir, ignore_errors=True)
                return AcquisitionResult(
                    success=False,
                    status="WORKSPACE_CREATION_FAILED",
                    message="Failed secure workspace path validation."
                )

            try:
                zip_resp = await client.get(
                    f"{self.BASE_URL}/repos/{owner}/{repo}/zipball/{base_branch}",
                    headers=self._headers()
                )
                if zip_resp.status_code != 200:
                    shutil.rmtree(workspace_dir, ignore_errors=True)
                    return AcquisitionResult(
                        success=False,
                        status="ACQUISITION_FAILED",
                        message=f"GitHub returned HTTP {zip_resp.status_code} downloading repository zipball."
                    )

                with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zip_file:
                    for member in zip_file.infolist():
                        is_safe, target_path = self._is_safe_zip_entry(workspace_dir, member.filename)
                        if not is_safe:
                            shutil.rmtree(workspace_dir, ignore_errors=True)
                            return AcquisitionResult(
                                success=False,
                                status="UNSAFE_ZIP_ENTRY",
                                message=f"Unsafe path traversal detected in repository archive: '{member.filename}'"
                            )

                        if member.is_dir() or member.filename.endswith("/") or member.filename.endswith("\\"):
                            os.makedirs(target_path, exist_ok=True)
                        else:
                            os.makedirs(os.path.dirname(target_path), exist_ok=True)
                            with zip_file.open(member) as source, open(target_path, "wb") as target:
                                shutil.copyfileobj(source, target)

                items = os.listdir(workspace_dir)
                if len(items) == 1:
                    single_item = os.path.join(workspace_dir, items[0])
                    if os.path.isdir(single_item):
                        for sub in os.listdir(single_item):
                            shutil.move(os.path.join(single_item, sub), workspace_dir)
                        os.rmdir(single_item)

                return AcquisitionResult(
                    success=True,
                    workspace_path=abs_workspace,
                    repository=f"{owner}/{repo}",
                    base_branch=base_branch,
                    status="ACQUIRED",
                    message=f"Repository '{owner}/{repo}' ({base_branch}) successfully acquired into isolated workspace."
                )
            except Exception as e:
                shutil.rmtree(workspace_dir, ignore_errors=True)
                clean_err = str(e).replace(self.token, "***") if self.token else str(e)
                return AcquisitionResult(
                    success=False,
                    status="ACQUISITION_ERROR",
                    message=f"Failed to acquire repository contents: {clean_err}"
                )

    async def create_branch_and_commit(
        self,
        github_repo: str,
        files_map: Dict[str, str],
        base_branch: str = "main",
        commit_message: Optional[str] = None,
        branch_prefix: str = "fix/api-healer-migration"
    ) -> CommitResult:
        if not self.is_configured():
            return CommitResult(
                success=False,
                status="NOT_CONFIGURED",
                message="GitHub integration is not configured. Server GITHUB_TOKEN environment variable is missing."
            )

        if not github_repo or "/" not in github_repo:
            return CommitResult(
                success=False,
                status="INVALID_REPOSITORY",
                message=f"Invalid GitHub repository specification: '{github_repo}'"
            )

        parts = github_repo.strip().rstrip("/").split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return CommitResult(
                success=False,
                status="INVALID_REPOSITORY",
                message=f"Invalid GitHub repository format: '{github_repo}'"
            )

        owner, repo = parts[0], parts[1]

        pattern = re.compile(r"^[a-zA-Z0-9_.-]+$")
        if not pattern.match(owner) or not pattern.match(repo):
            return CommitResult(
                success=False,
                status="INVALID_REPOSITORY",
                message="Invalid characters in GitHub owner or repository name."
            )

        branch_pattern = re.compile(r"^[a-zA-Z0-9_/.-]+$")
        if not base_branch or not branch_pattern.match(base_branch) or ".." in base_branch:
            return CommitResult(
                success=False,
                status="INVALID_BRANCH",
                message=f"Invalid base branch specification: '{base_branch}'"
            )

        if not files_map:
            return CommitResult(
                success=False,
                status="NO_CHANGES",
                message="No changed files were provided for GitHub commit."
            )

        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            try:
                ref_resp = await client.get(
                    f"{self.BASE_URL}/repos/{owner}/{repo}/git/ref/heads/{base_branch}",
                    headers=self._headers()
                )
                if ref_resp.status_code == 404:
                    return CommitResult(
                        success=False,
                        status="BASE_BRANCH_NOT_FOUND",
                        message=f"Base branch '{base_branch}' or repository '{owner}/{repo}' not found on GitHub."
                    )
                elif ref_resp.status_code == 403:
                    return CommitResult(
                        success=False,
                        status="PERMISSION_DENIED",
                        message="GitHub API access denied (403). Check GITHUB_TOKEN permissions."
                    )
                ref_resp.raise_for_status()
                base_sha = ref_resp.json().get("object", {}).get("sha")
                if not base_sha:
                    return CommitResult(
                        success=False,
                        status="BASE_BRANCH_ERROR",
                        message=f"Could not retrieve commit SHA for branch '{base_branch}'."
                    )
            except httpx.HTTPStatusError as e:
                return CommitResult(
                    success=False,
                    status=f"HTTP_{e.response.status_code}",
                    message=f"GitHub API error ({e.response.status_code}) fetching base branch."
                )
            except httpx.HTTPError as e:
                return CommitResult(
                    success=False,
                    status="GITHUB_NETWORK_ERROR",
                    message=f"Network error communicating with GitHub: {str(e)}"
                )

            branch_name = f"{branch_prefix}-{uuid.uuid4().hex[:8]}"
            try:
                create_ref_resp = await client.post(
                    f"{self.BASE_URL}/repos/{owner}/{repo}/git/refs",
                    headers=self._headers(),
                    json={
                        "ref": f"refs/heads/{branch_name}",
                        "sha": base_sha
                    }
                )
                if create_ref_resp.status_code == 422:
                    branch_name = f"{branch_prefix}-{uuid.uuid4().hex[:8]}"
                    create_ref_resp = await client.post(
                        f"{self.BASE_URL}/repos/{owner}/{repo}/git/refs",
                        headers=self._headers(),
                        json={
                            "ref": f"refs/heads/{branch_name}",
                            "sha": base_sha
                        }
                    )
                create_ref_resp.raise_for_status()
            except httpx.HTTPError as e:
                return CommitResult(
                    success=False,
                    status="BRANCH_CREATION_FAILED",
                    message=f"Failed to create branch '{branch_name}': {str(e)}"
                )

            commit_sha = base_sha
            committed_files = []

            for rel_path, content in files_map.items():
                try:
                    existing_sha = None
                    file_resp = await client.get(
                        f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{rel_path}",
                        headers=self._headers(),
                        params={"ref": branch_name}
                    )
                    if file_resp.status_code == 200:
                        existing_sha = file_resp.json().get("sha")

                    b64_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
                    msg = commit_message or f"fix(api): migrate API contract changes for {rel_path}"
                    put_payload = {
                        "message": msg,
                        "content": b64_content,
                        "branch": branch_name
                    }
                    if existing_sha:
                        put_payload["sha"] = existing_sha

                    put_resp = await client.put(
                        f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{rel_path}",
                        headers=self._headers(),
                        json=put_payload
                    )
                    put_resp.raise_for_status()
                    commit_sha = put_resp.json().get("commit", {}).get("sha", base_sha)
                    committed_files.append(rel_path)
                except httpx.HTTPError as e:
                    return CommitResult(
                        success=False,
                        status="FILE_COMMIT_FAILED",
                        message=f"Failed to commit file '{rel_path}': {str(e)}"
                    )

            return CommitResult(
                success=True,
                status="COMMITTED",
                repository=f"{owner}/{repo}",
                base_branch=base_branch,
                head_branch=branch_name,
                commit_sha=commit_sha,
                files_committed=committed_files,
                message="Validated API-Healer migration committed to GitHub branch."
            )

    async def create_pull_request(
        self,
        github_repo: str,
        files_map: Dict[str, str],
        base_branch: str = "main",
        head_branch: Optional[str] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        branch_prefix: str = "fix/api-healer-migration"
    ) -> PullRequestResult:
        if not self.is_configured():
            return PullRequestResult(
                success=False,
                status="NOT_CONFIGURED",
                message="GitHub integration is not configured. Server GITHUB_TOKEN environment variable is missing."
            )

        if not github_repo or "/" not in github_repo:
            return PullRequestResult(
                success=False,
                status="INVALID_REPOSITORY",
                message=f"Invalid GitHub repository specification: '{github_repo}'"
            )

        parts = github_repo.strip().rstrip("/").split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return PullRequestResult(
                success=False,
                status="INVALID_REPOSITORY",
                message=f"Invalid GitHub repository format: '{github_repo}'"
            )

        owner, repo = parts[0], parts[1]

        if not files_map and not head_branch:
            return PullRequestResult(
                success=False,
                status="NO_FILES_TO_COMMIT",
                message="No transformed files were provided for Pull Request creation."
            )

        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            # 1. Verify Base Branch
            try:
                ref_resp = await client.get(
                    f"{self.BASE_URL}/repos/{owner}/{repo}/git/ref/heads/{base_branch}",
                    headers=self._headers()
                )
                if ref_resp.status_code == 404:
                    return PullRequestResult(
                        success=False,
                        status="BASE_BRANCH_NOT_FOUND",
                        message=f"Base branch '{base_branch}' or repository '{owner}/{repo}' not found on GitHub."
                    )
                elif ref_resp.status_code == 403:
                    return PullRequestResult(
                        success=False,
                        status="PERMISSION_DENIED",
                        message="GitHub API access denied (403). Check GITHUB_TOKEN permissions."
                    )
                ref_resp.raise_for_status()
                base_sha = ref_resp.json().get("object", {}).get("sha")
            except httpx.HTTPStatusError as e:
                return PullRequestResult(
                    success=False,
                    status=f"HTTP_{e.response.status_code}",
                    message=f"GitHub API error ({e.response.status_code}) fetching base branch."
                )
            except httpx.HTTPError as e:
                return PullRequestResult(
                    success=False,
                    status="GITHUB_NETWORK_ERROR",
                    message=f"Network error communicating with GitHub: {str(e)}"
                )

            # 2. Branch & Commit Resolution
            commit_sha = base_sha
            branch_name = head_branch

            if not branch_name:
                commit_res = await self.create_branch_and_commit(
                    github_repo=github_repo,
                    files_map=files_map,
                    base_branch=base_branch,
                    branch_prefix=branch_prefix
                )
                if not commit_res.success:
                    return PullRequestResult(
                        success=False,
                        status=commit_res.status,
                        message=commit_res.message
                    )
                branch_name = commit_res.head_branch
                commit_sha = commit_res.commit_sha
            else:
                # Verify existing head branch
                try:
                    head_ref_resp = await client.get(
                        f"{self.BASE_URL}/repos/{owner}/{repo}/git/ref/heads/{branch_name}",
                        headers=self._headers()
                    )
                    if head_ref_resp.status_code == 404:
                        return PullRequestResult(
                            success=False,
                            status="BRANCH_NOT_FOUND",
                            message=f"Migration branch '{branch_name}' not found on GitHub."
                        )
                    head_ref_resp.raise_for_status()
                    commit_sha = head_ref_resp.json().get("object", {}).get("sha", base_sha)
                except httpx.HTTPError as e:
                    return PullRequestResult(
                        success=False,
                        status="BRANCH_CHECK_FAILED",
                        message=f"Failed to verify migration branch '{branch_name}': {str(e)}"
                    )

            # 3. DUPLICATE PR PROTECTION CHECK
            try:
                existing_prs_resp = await client.get(
                    f"{self.BASE_URL}/repos/{owner}/{repo}/pulls",
                    headers=self._headers(),
                    params={"head": f"{owner}:{branch_name}", "base": base_branch, "state": "open"}
                )
                if existing_prs_resp.status_code == 200:
                    open_prs = existing_prs_resp.json()
                    if open_prs and isinstance(open_prs, list) and len(open_prs) > 0:
                        existing = open_prs[0]
                        return PullRequestResult(
                            success=True,
                            pr_number=existing.get("number"),
                            pr_url=existing.get("html_url"),
                            repository=f"{owner}/{repo}",
                            head_branch=branch_name,
                            base_branch=base_branch,
                            commit_sha=commit_sha,
                            title=existing.get("title"),
                            status="PR_ALREADY_EXISTS",
                            message=f"Pull Request #{existing.get('number')} already exists on GitHub."
                        )
            except Exception:
                pass

            # 4. Create Pull Request
            pr_title = title or "fix(api): automated API-Healer migration"
            pr_body = body or (
                "### API-Healer Automated Migration Report\n\n"
                "API-Healer detected a breaking API contract update and applied safe, "
                "formatting-preserving LibCST code transformations.\n\n"
                "- **Validation:** Passed native Python AST syntax validation.\n"
                "- **Human Review:** Required before merging."
            )
            try:
                pr_resp = await client.post(
                    f"{self.BASE_URL}/repos/{owner}/{repo}/pulls",
                    headers=self._headers(),
                    json={
                        "title": pr_title,
                        "body": pr_body,
                        "head": branch_name,
                        "base": base_branch
                    }
                )
                if pr_resp.status_code == 422:
                    return PullRequestResult(
                        success=False,
                        status="PR_ALREADY_EXISTS",
                        message="GitHub rejected Pull Request creation (422). Check if PR already exists."
                    )
                pr_resp.raise_for_status()
                pr_data = pr_resp.json()

                return PullRequestResult(
                    success=True,
                    pr_number=pr_data.get("number"),
                    pr_url=pr_data.get("html_url"),
                    repository=f"{owner}/{repo}",
                    head_branch=branch_name,
                    base_branch=base_branch,
                    commit_sha=commit_sha,
                    title=pr_title,
                    status="PR_CREATED",
                    message=f"Pull Request #{pr_data.get('number')} created successfully."
                )
            except httpx.HTTPError as e:
                return PullRequestResult(
                    success=False,
                    status="PR_CREATION_FAILED",
                    message=f"Failed to create Pull Request: {str(e)}"
                )
