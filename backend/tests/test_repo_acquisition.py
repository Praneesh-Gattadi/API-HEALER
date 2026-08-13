import os
import zipfile
import io
import tempfile
import pytest
import httpx
from unittest.mock import patch
from app.models.github import AcquireRepoRequest, AcquisitionResult, CleanupWorkspaceRequest
from app.services.github_service import GitHubService

orig_async_client = httpx.AsyncClient

def get_client_with_transport(transport):
    def _factory(*args, **kwargs):
        kwargs["transport"] = transport
        return orig_async_client(*args, **kwargs)
    return _factory

def create_zip_with_members(members_dict):
    """
    members_dict: rel_filename -> content_bytes
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for filename, content in members_dict.items():
            zf.writestr(filename, content)
    return buf.getvalue()

@pytest.mark.asyncio
async def test_acquire_missing_github_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    service = GitHubService()
    result = await service.acquire_repository("owner/repo", "main")
    assert not result.success
    assert result.status == "NOT_CONFIGURED"

@pytest.mark.asyncio
async def test_acquire_invalid_owner():
    service = GitHubService(token="dummy_token")
    result = await service.acquire_repository("owner/invalid/repo", "main")
    assert not result.success
    assert result.status == "INVALID_REPOSITORY"

@pytest.mark.asyncio
async def test_acquire_invalid_repo_name():
    service = GitHubService(token="dummy_token")
    result = await service.acquire_repository("owner/repo;rm -rf", "main")
    assert not result.success
    assert result.status == "INVALID_REPOSITORY"

@pytest.mark.asyncio
async def test_acquire_invalid_branch():
    service = GitHubService(token="dummy_token")
    result = await service.acquire_repository("owner/repo", "../main")
    assert not result.success
    assert result.status == "INVALID_BRANCH"

@pytest.mark.asyncio
async def test_acquire_repo_not_found():
    service = GitHubService(token="dummy_token")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        result = await service.acquire_repository("owner/repo", "main")
    assert not result.success
    assert result.status == "REPOSITORY_NOT_FOUND"

@pytest.mark.asyncio
async def test_acquire_auth_failure_403():
    service = GitHubService(token="dummy_token")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "Forbidden"})

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        result = await service.acquire_repository("owner/repo", "main")
    assert not result.success
    assert result.status == "PERMISSION_DENIED"

@pytest.mark.asyncio
async def test_acquire_branch_not_found():
    service = GitHubService(token="dummy_token")

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "/repos/owner/repo" in url_str and "/git/ref" not in url_str:
            return httpx.Response(200, json={"full_name": "owner/repo"})
        elif "/git/ref/heads/main" in url_str:
            return httpx.Response(404, json={"message": "Not Found"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        result = await service.acquire_repository("owner/repo", "main")
    assert not result.success
    assert result.status == "BRANCH_NOT_FOUND"

# ==========================================
# G5.1 ZIP SLIP & PATH TRAVERSAL SECURITY TESTS
# ==========================================

@pytest.mark.asyncio
async def test_zip_slip_dotdot_traversal():
    service = GitHubService(token="dummy_token")
    bad_zip = create_zip_with_members({"../outside.txt": b"hacked"})

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "/repos/owner/repo" in url_str and "/git/ref" not in url_str and "/zipball" not in url_str:
            return httpx.Response(200, json={"full_name": "owner/repo"})
        elif "/git/ref/heads/main" in url_str:
            return httpx.Response(200, json={"object": {"sha": "12345"}})
        elif "/zipball/main" in url_str:
            return httpx.Response(200, content=bad_zip)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        result = await service.acquire_repository("owner/repo", "main")

    assert not result.success
    assert result.status == "UNSAFE_ZIP_ENTRY"
    assert result.workspace_path is None or not os.path.exists(result.workspace_path)

@pytest.mark.asyncio
async def test_zip_slip_windows_traversal():
    service = GitHubService(token="dummy_token")
    bad_zip = create_zip_with_members({"..\\..\\outside.txt": b"hacked"})

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "/repos/owner/repo" in url_str and "/git/ref" not in url_str and "/zipball" not in url_str:
            return httpx.Response(200, json={"full_name": "owner/repo"})
        elif "/git/ref/heads/main" in url_str:
            return httpx.Response(200, json={"object": {"sha": "12345"}})
        elif "/zipball/main" in url_str:
            return httpx.Response(200, content=bad_zip)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        result = await service.acquire_repository("owner/repo", "main")

    assert not result.success
    assert result.status == "UNSAFE_ZIP_ENTRY"

@pytest.mark.asyncio
async def test_zip_slip_one_malicious_member_among_valid():
    service = GitHubService(token="dummy_token")
    bad_zip = create_zip_with_members({
        "test-repo-main/main.py": b"print('valid')",
        "test-repo-main/../../outside.txt": b"malicious",
    })

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "/repos/owner/repo" in url_str and "/git/ref" not in url_str and "/zipball" not in url_str:
            return httpx.Response(200, json={"full_name": "owner/repo"})
        elif "/git/ref/heads/main" in url_str:
            return httpx.Response(200, json={"object": {"sha": "12345"}})
        elif "/zipball/main" in url_str:
            return httpx.Response(200, content=bad_zip)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        result = await service.acquire_repository("owner/repo", "main")

    assert not result.success
    assert result.status == "UNSAFE_ZIP_ENTRY"

@pytest.mark.asyncio
async def test_valid_zip_nested_structure():
    service = GitHubService(token="dummy_token")
    good_zip = create_zip_with_members({
        "repo-main/README.md": b"# Test Repo",
        "repo-main/src/app.py": b"import os",
        "repo-main/src/utils/helpers.py": b"def help(): pass",
    })

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "/repos/owner/repo" in url_str and "/git/ref" not in url_str and "/zipball" not in url_str:
            return httpx.Response(200, json={"full_name": "owner/repo"})
        elif "/git/ref/heads/main" in url_str:
            return httpx.Response(200, json={"object": {"sha": "12345"}})
        elif "/zipball/main" in url_str:
            return httpx.Response(200, content=good_zip)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        result = await service.acquire_repository("owner/repo", "main")

    assert result.success
    assert result.status == "ACQUIRED"
    ws = result.workspace_path
    assert os.path.exists(os.path.join(ws, "README.md"))
    assert os.path.exists(os.path.join(ws, "src", "app.py"))
    assert os.path.exists(os.path.join(ws, "src", "utils", "helpers.py"))

    GitHubService.cleanup_workspace(ws)

# ==========================================
# G5.1 TOKEN LEAKAGE & SECURITY BOUNDARY TESTS
# ==========================================

@pytest.mark.asyncio
async def test_token_leakage_security():
    secret_token = "TEST_SECRET_TOKEN_DO_NOT_LEAK"
    service = GitHubService(token=secret_token)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": f"Internal Server Error with {secret_token}"})

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        result = await service.acquire_repository("owner/repo", "main")

    assert not result.success
    assert secret_token not in result.message
    assert secret_token not in str(result.model_dump())

def test_cleanup_security_boundaries():
    temp_dir = os.path.realpath(os.path.abspath(tempfile.gettempdir()))
    repo_root = os.path.realpath(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    user_home = os.path.realpath(os.path.expanduser("~"))

    # Valid created temp workspace
    ws_dir = tempfile.mkdtemp(prefix="api_healer_workspace_test_")
    assert GitHubService.cleanup_workspace(ws_dir) == True

    # Prefix collision attack: /tmp/api_healer_workspace_abc_evil
    fake_collision = os.path.join(temp_dir, "api_healer_workspace_evil_other")
    assert GitHubService.cleanup_workspace(fake_collision) == False

    # Path traversal inside cleanup argument
    traversal_path = os.path.join(temp_dir, "api_healer_workspace_abc", "..", "other")
    assert GitHubService.cleanup_workspace(traversal_path) == False

    # System boundaries
    assert GitHubService.cleanup_workspace(temp_dir) == False
    assert GitHubService.cleanup_workspace(repo_root) == False
    assert GitHubService.cleanup_workspace(user_home) == False
    assert GitHubService.cleanup_workspace("/") == False

@pytest.mark.asyncio
async def test_concurrent_workspaces_are_unique():
    service = GitHubService(token="dummy_token")
    zip_data = create_zip_with_members({"repo-main/main.py": b"print('unique')"})

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "/repos/owner/repo" in url_str and "/git/ref" not in url_str and "/zipball" not in url_str:
            return httpx.Response(200, json={"full_name": "owner/repo"})
        elif "/git/ref/heads/main" in url_str:
            return httpx.Response(200, json={"object": {"sha": "12345"}})
        elif "/zipball/main" in url_str:
            return httpx.Response(200, content=zip_data)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        res1 = await service.acquire_repository("owner/repo", "main")
        res2 = await service.acquire_repository("owner/repo", "main")

    assert res1.success and res2.success
    assert res1.workspace_path != res2.workspace_path

    GitHubService.cleanup_workspace(res1.workspace_path)
    GitHubService.cleanup_workspace(res2.workspace_path)
