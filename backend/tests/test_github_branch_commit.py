import os
import pytest
import httpx
from unittest.mock import patch
from app.models.github import CreateBranchCommitRequest, CommitResult
from app.services.github_service import GitHubService

orig_async_client = httpx.AsyncClient

def get_client_with_transport(transport):
    def _factory(*args, **kwargs):
        kwargs["transport"] = transport
        return orig_async_client(*args, **kwargs)
    return _factory

@pytest.mark.asyncio
async def test_commit_missing_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    service = GitHubService()
    res = await service.create_branch_and_commit("owner/repo", {"main.py": "print('hello')"}, "main")
    assert not res.success
    assert res.status == "NOT_CONFIGURED"

@pytest.mark.asyncio
async def test_commit_invalid_repository():
    service = GitHubService(token="dummy")
    res = await service.create_branch_and_commit("invalid_repo", {"main.py": "print('hello')"}, "main")
    assert not res.success
    assert res.status == "INVALID_REPOSITORY"

@pytest.mark.asyncio
async def test_commit_invalid_base_branch():
    service = GitHubService(token="dummy")
    res = await service.create_branch_and_commit("owner/repo", {"main.py": "print('hello')"}, "../main")
    assert not res.success
    assert res.status == "INVALID_BRANCH"

@pytest.mark.asyncio
async def test_commit_no_changed_files():
    service = GitHubService(token="dummy")
    res = await service.create_branch_and_commit("owner/repo", {}, "main")
    assert not res.success
    assert res.status == "NO_CHANGES"

@pytest.mark.asyncio
async def test_commit_base_branch_404():
    service = GitHubService(token="dummy")

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        res = await service.create_branch_and_commit("owner/repo", {"main.py": "print('hello')"}, "main")

    assert not res.success
    assert res.status == "BASE_BRANCH_NOT_FOUND"

@pytest.mark.asyncio
async def test_commit_github_api_403():
    service = GitHubService(token="dummy")

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "Forbidden"})

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        res = await service.create_branch_and_commit("owner/repo", {"main.py": "print('hello')"}, "main")

    assert not res.success
    assert res.status == "PERMISSION_DENIED"

@pytest.mark.asyncio
async def test_successful_single_and_multi_file_commit():
    service = GitHubService(token="secret_token_g7")
    urls_called = []

    def handler(req: httpx.Request) -> httpx.Response:
        url_str = str(req.url)
        urls_called.append(url_str)
        if "/git/ref/heads/main" in url_str:
            return httpx.Response(200, json={"object": {"sha": "base_sha_123"}})
        elif "/git/refs" in url_str and req.method == "POST":
            return httpx.Response(201, json={"ref": "refs/heads/fix/api-healer-migration-12345678"})
        elif "/contents/" in url_str and req.method == "GET":
            return httpx.Response(200, json={"sha": "old_file_sha"})
        elif "/contents/" in url_str and req.method == "PUT":
            return httpx.Response(200, json={"commit": {"sha": "new_commit_sha_999"}})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    files_map = {
        "main.py": "from pydantic import BaseModel\nclass User(BaseModel):\n    account_id: str\n",
        "models.py": "class Account:\n    pass\n"
    }

    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        res = await service.create_branch_and_commit(
            github_repo="owner/repo",
            files_map=files_map,
            base_branch="main",
            commit_message="fix(api): migrate user_id to account_id"
        )

    assert res.success
    assert res.status == "COMMITTED"
    assert res.repository == "owner/repo"
    assert res.base_branch == "main"
    assert res.head_branch.startswith("fix/api-healer-migration-")
    assert res.commit_sha == "new_commit_sha_999"
    assert len(res.files_committed) == 2
    assert "main.py" in res.files_committed
    assert "models.py" in res.files_committed

    # G7 RULE: Verify zero Pull Request endpoints called
    assert not any("/pulls" in u for u in urls_called)

@pytest.mark.asyncio
async def test_token_leakage_in_commit_errors():
    token = "TEST_SECRET_TOKEN_G7_LEAK"
    service = GitHubService(token=token)

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": f"Failure with {token}"})

    transport = httpx.MockTransport(handler)
    with patch("httpx.AsyncClient", get_client_with_transport(transport)):
        res = await service.create_branch_and_commit("owner/repo", {"main.py": "print()"}, "main")

    assert not res.success
    assert token not in res.message
    assert token not in str(res.model_dump())
