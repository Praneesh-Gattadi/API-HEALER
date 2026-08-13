import os
import tempfile
import pytest
import httpx
from unittest.mock import patch
from app.models.github import CreatePRRequest, PullRequestResult
from app.services.github_service import GitHubService
from app.api.v1.endpoints.github import is_safe_file_path, create_pull_request
from app.models.provider import ProviderConfig

orig_async_client = httpx.AsyncClient

def get_client_with_transport(transport):
    def _factory(*args, **kwargs):
        kwargs["transport"] = transport
        return orig_async_client(*args, **kwargs)
    return _factory

@pytest.mark.asyncio
async def test_missing_github_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    service = GitHubService()
    assert not service.is_configured()

    result = await service.create_pull_request(
        github_repo="owner/repo",
        files_map={"main.py": "print('hello')"}
    )
    assert not result.success
    assert result.status == "NOT_CONFIGURED"
    assert "missing" in result.message.lower()

@pytest.mark.asyncio
async def test_invalid_github_repo_format():
    service = GitHubService(token="dummy_token")
    result = await service.create_pull_request(
        github_repo="invalid_repo_name_without_slash",
        files_map={"main.py": "print('hello')"}
    )
    assert not result.success
    assert result.status == "INVALID_REPOSITORY"

@pytest.mark.asyncio
async def test_no_files_to_commit():
    service = GitHubService(token="dummy_token")
    result = await service.create_pull_request(
        github_repo="owner/repo",
        files_map={}
    )
    assert not result.success
    assert result.status == "NO_FILES_TO_COMMIT"

@pytest.mark.asyncio
async def test_base_branch_not_found():
    service = GitHubService(token="dummy_token")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        result = await service.create_pull_request(
            github_repo="owner/repo",
            files_map={"main.py": "print('hello')"}
        )
    assert not result.success
    assert result.status == "BASE_BRANCH_NOT_FOUND"

@pytest.mark.asyncio
async def test_github_403_permission_denied():
    service = GitHubService(token="dummy_token")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "Forbidden"})

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        result = await service.create_pull_request(
            github_repo="owner/repo",
            files_map={"main.py": "print('hello')"}
        )
    assert not result.success
    assert result.status == "PERMISSION_DENIED"

@pytest.mark.asyncio
async def test_successful_complete_pr_workflow():
    service = GitHubService(token="secret_token_123")

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "/git/ref/heads/main" in url_str:
            return httpx.Response(200, json={"object": {"sha": "base_commit_sha_123"}})
        elif "/git/refs" in url_str:
            return httpx.Response(201, json={"ref": "refs/heads/fix/api-healer-migration-12345678"})
        elif "/contents/main.py" in url_str:
            if request.method == "GET":
                return httpx.Response(404, json={"message": "Not Found"})
            elif request.method == "PUT":
                return httpx.Response(200, json={"commit": {"sha": "new_commit_sha_456"}})
        elif "/pulls" in url_str:
            return httpx.Response(201, json={
                "number": 42,
                "html_url": "https://github.com/owner/repo/pull/42"
            })
        return httpx.Response(404, json={"message": "Not Found"})

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        result = await service.create_pull_request(
            github_repo="owner/repo",
            files_map={"main.py": "class User:\n    account_id: str\n"},
            title="fix(api): update user_id to account_id"
        )

    assert result.success
    assert result.pr_number == 42
    assert result.pr_url == "https://github.com/owner/repo/pull/42"
    assert result.repository == "owner/repo"
    assert result.commit_sha == "new_commit_sha_456"
    assert "secret_token_123" not in result.message
    assert "secret_token_123" not in str(result.model_dump())

def test_is_safe_file_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        abs_repo = os.path.abspath(tmpdir)
        safe_file = os.path.join(abs_repo, "app", "main.py")
        unsafe_traversal = os.path.abspath(os.path.join(abs_repo, "..", "secret.txt"))
        env_file = os.path.join(abs_repo, ".env")

        assert is_safe_file_path(abs_repo, safe_file) == True
        assert is_safe_file_path(abs_repo, unsafe_traversal) == False
        assert is_safe_file_path(abs_repo, env_file) == False

@pytest.mark.asyncio
async def test_endpoint_missing_token_returns_clean_result(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    req = CreatePRRequest(
        github_repo="owner/repo",
        repository_path="./demo/consumer_app"
    )
    result = await create_pull_request(req)
    assert not result.success
    assert result.status == "NOT_CONFIGURED"

def test_provider_model_optional_github_repo():
    p = ProviderConfig(
        id="test_id",
        name="test_name",
        spec_url="http://localhost:8080/demo/v1.json",
        repository_path="demo/consumer_app"
    )
    assert p.github_repo is None
