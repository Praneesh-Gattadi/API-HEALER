import os
import pytest
import httpx
from unittest.mock import patch
from app.models.github import CreatePRRequest, PullRequestResult
from app.services.github_service import GitHubService

orig_async_client = httpx.AsyncClient

def get_client_with_transport(transport):
    def _factory(*args, **kwargs):
        kwargs["transport"] = transport
        return orig_async_client(*args, **kwargs)
    return _factory

@pytest.mark.asyncio
async def test_pr_missing_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    service = GitHubService()
    res = await service.create_pull_request("owner/repo", {"main.py": "print()"}, "main")
    assert not res.success
    assert res.status == "NOT_CONFIGURED"

@pytest.mark.asyncio
async def test_pr_invalid_repository():
    service = GitHubService(token="dummy")
    res = await service.create_pull_request("invalid_repo", {"main.py": "print()"}, "main")
    assert not res.success
    assert res.status == "INVALID_REPOSITORY"

@pytest.mark.asyncio
async def test_pr_base_branch_404():
    service = GitHubService(token="dummy")

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        res = await service.create_pull_request("owner/repo", {"main.py": "print()"}, "main")

    assert not res.success
    assert res.status == "BASE_BRANCH_NOT_FOUND"

@pytest.mark.asyncio
async def test_pr_permission_denied_403():
    service = GitHubService(token="dummy")

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "Forbidden"})

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        res = await service.create_pull_request("owner/repo", {"main.py": "print()"}, "main")

    assert not res.success
    assert res.status == "PERMISSION_DENIED"

@pytest.mark.asyncio
async def test_pr_duplicate_detection():
    service = GitHubService(token="dummy_token")

    def handler(req: httpx.Request) -> httpx.Response:
        url_str = str(req.url)
        if "/git/ref/heads/main" in url_str:
            return httpx.Response(200, json={"object": {"sha": "base_sha_123"}})
        elif "/git/ref/heads/fix/api-healer-migration-test" in url_str:
            return httpx.Response(200, json={"object": {"sha": "head_sha_456"}})
        elif "/pulls" in url_str and req.method == "GET":
            return httpx.Response(200, json=[{
                "number": 88,
                "html_url": "https://github.com/owner/repo/pull/88",
                "title": "fix(api): user_id -> account_id"
            }])
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        res = await service.create_pull_request(
            github_repo="owner/repo",
            files_map={},
            base_branch="main",
            head_branch="fix/api-healer-migration-test"
        )

    assert res.success
    assert res.status == "PR_ALREADY_EXISTS"
    assert res.pr_number == 88
    assert res.pr_url == "https://github.com/owner/repo/pull/88"

@pytest.mark.asyncio
async def test_successful_real_pr_creation():
    service = GitHubService(token="secret_token_g8")

    def handler(req: httpx.Request) -> httpx.Response:
        url_str = str(req.url)
        if "/git/ref/heads/main" in url_str:
            return httpx.Response(200, json={"object": {"sha": "base_sha_123"}})
        elif "/git/ref/heads/fix/api-healer-migration-test" in url_str:
            return httpx.Response(200, json={"object": {"sha": "head_sha_456"}})
        elif "/pulls" in url_str and req.method == "GET":
            return httpx.Response(200, json=[])
        elif "/pulls" in url_str and req.method == "POST":
            return httpx.Response(201, json={
                "number": 99,
                "html_url": "https://github.com/owner/repo/pull/99"
            })
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        res = await service.create_pull_request(
            github_repo="owner/repo",
            files_map={},
            base_branch="main",
            head_branch="fix/api-healer-migration-test",
            title="fix(api): migrate user_id to account_id",
            body="### API-Healer Report\n- AST syntax validated"
        )

    assert res.success
    assert res.status == "PR_CREATED"
    assert res.pr_number == 99
    assert res.pr_url == "https://github.com/owner/repo/pull/99"
    assert res.commit_sha == "head_sha_456"
    assert res.head_branch == "fix/api-healer-migration-test"
    assert res.base_branch == "main"

@pytest.mark.asyncio
async def test_token_leakage_in_pr_creation():
    token = "TEST_SECRET_TOKEN_G8_LEAK"
    service = GitHubService(token=token)

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": f"Failure with {token}"})

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        res = await service.create_pull_request("owner/repo", {"main.py": "print()"}, "main")

    assert not res.success
    assert token not in res.message
    assert token not in str(res.model_dump())
