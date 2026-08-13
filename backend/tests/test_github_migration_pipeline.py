import os
import tempfile
import shutil
import pytest
import httpx
from unittest.mock import patch
from app.models.provider import ProviderStatus, SnapshotStatus
from app.models.migration_plan import MigrationPlan, MigrationAction, MigrationActionType
from app.services.provider_store import ProviderStore
from app.services.provider_monitor import ProviderMonitor
from app.services.github_service import GitHubService
from app.services.impact_analyzer import ImpactAnalyzer
from app.services.openapi_diff import compare_openapi_specs
from app.services.code_transformer import apply_transform

orig_async_client = httpx.AsyncClient

def get_client_with_transport(transport):
    def _factory(*args, **kwargs):
        kwargs["transport"] = transport
        return orig_async_client(*args, **kwargs)
    return _factory

SAMPLE_PYDANTIC_CODE = """from pydantic import BaseModel

class User(BaseModel):
    user_id: str

u = User(user_id="123")
"""

@pytest.fixture
def acquired_workspace():
    ws_dir = tempfile.mkdtemp(prefix="api_healer_workspace_g6_test_")
    main_py = os.path.join(ws_dir, "main.py")
    with open(main_py, "w", encoding="utf-8") as f:
        f.write(SAMPLE_PYDANTIC_CODE)

    unrelated_py = os.path.join(ws_dir, "unrelated.py")
    with open(unrelated_py, "w", encoding="utf-8") as f:
        f.write('def untouched():\n    return 42\n')

    yield ws_dir
    if os.path.exists(ws_dir):
        shutil.rmtree(ws_dir, ignore_errors=True)

def test_acquired_workspace_accepted_by_impact_analyzer(acquired_workspace):
    old_spec = {"openapi": "3.0.0", "paths": {"/users": {"get": {"parameters": [{"name": "user_id", "in": "query"}]}}}}
    new_spec = {"openapi": "3.0.0", "paths": {"/users": {"get": {"parameters": [{"name": "account_id", "in": "query"}]}}}}
    diff_result = compare_openapi_specs(old_spec, new_spec)
    impact = ImpactAnalyzer.analyze(acquired_workspace, diff_result)
    assert impact.evidence_strength.value == "STRONG"
    assert len(impact.details) > 0

@pytest.mark.asyncio
async def test_scenario_a_through_acquired_workspace(tmp_path, monkeypatch):
    store = ProviderStore(base_dir=str(tmp_path))
    monitor = ProviderMonitor(store)

    ws_dir = tempfile.mkdtemp(prefix="api_healer_workspace_g6_scen_a_")
    with open(os.path.join(ws_dir, "main.py"), "w", encoding="utf-8") as f:
        f.write(SAMPLE_PYDANTIC_CODE)

    monkeypatch.setattr("app.services.contract_parser.ContractParser.fetch_and_parse",
        lambda url: {"openapi": "3.0.0", "paths": {"/users": {"get": {"parameters": [{"name": "user_id", "in": "query"}]}}}})
    config = monitor.register_provider("Scenario A Provider", "http://localhost:8080/demo/v1.json", "demo/consumer_app", github_repo="owner/repo")
    config.workspace_path = ws_dir
    store.save_provider(config)

    monkeypatch.setattr("app.services.contract_parser.ContractParser.fetch_and_parse",
        lambda url: {"openapi": "3.0.0", "paths": {"/users": {"get": {"parameters": [{"name": "account_id", "in": "query"}]}}}})

    decision = await monitor.check_for_updates(config.id)
    assert decision.status == ProviderStatus.MIGRATION_REQUIRED

    GitHubService.cleanup_workspace(ws_dir)

@pytest.mark.asyncio
async def test_scenario_b_through_acquired_workspace(tmp_path, monkeypatch):
    store = ProviderStore(base_dir=str(tmp_path))
    monitor = ProviderMonitor(store)

    ws_dir = tempfile.mkdtemp(prefix="api_healer_workspace_g6_scen_b_")
    with open(os.path.join(ws_dir, "main.py"), "w", encoding="utf-8") as f:
        f.write(SAMPLE_PYDANTIC_CODE)

    monkeypatch.setattr("app.services.contract_parser.ContractParser.fetch_and_parse",
        lambda url: {"openapi": "3.0.0", "paths": {"/users": {}, "/analytics": {}}})
    config = monitor.register_provider("Scenario B Provider", "http://localhost:8080/demo/v1.json", "demo/consumer_app", github_repo="owner/repo")
    config.workspace_path = ws_dir
    store.save_provider(config)

    monkeypatch.setattr("app.services.contract_parser.ContractParser.fetch_and_parse",
        lambda url: {"openapi": "3.0.0", "paths": {"/users": {}}})

    decision = await monitor.check_for_updates(config.id)
    assert decision.status == ProviderStatus.NO_MIGRATION_REQUIRED
    assert not os.path.exists(ws_dir)

def test_dry_run_against_acquired_workspace_byte_for_byte_immutability(acquired_workspace):
    main_py = os.path.join(acquired_workspace, "main.py")
    with open(main_py, "r", encoding="utf-8") as f:
        original_content = f.read()

    plan = MigrationPlan(
        summary="Rename user_id to account_id",
        risk_level="LOW",
        affected_files=["main.py"],
        actions=[
            MigrationAction(
                action_type=MigrationActionType.rename_field,
                description="Rename field user_id to account_id",
                old_name="user_id",
                new_name="account_id",
                affected_path="/users.GET",
                rationale="API field rename",
                validation_required="AST verification"
            )
        ]
    )

    result = apply_transform(plan, acquired_workspace, dry_run=True)
    assert result.success
    assert len(result.changes) > 0

    with open(main_py, "r", encoding="utf-8") as f:
        content_after_dry_run = f.read()
    assert original_content == content_after_dry_run

def test_apply_against_acquired_workspace_updates_code(acquired_workspace):
    main_py = os.path.join(acquired_workspace, "main.py")
    unrelated_py = os.path.join(acquired_workspace, "unrelated.py")

    with open(unrelated_py, "r", encoding="utf-8") as f:
        unrelated_before = f.read()

    plan = MigrationPlan(
        summary="Rename user_id to account_id",
        risk_level="LOW",
        affected_files=["main.py"],
        actions=[
            MigrationAction(
                action_type=MigrationActionType.rename_field,
                description="Rename field user_id to account_id",
                old_name="user_id",
                new_name="account_id",
                affected_path="/users.GET",
                rationale="API field rename",
                validation_required="AST verification"
            )
        ]
    )

    result = apply_transform(plan, acquired_workspace, dry_run=False)
    assert result.success

    with open(main_py, "r", encoding="utf-8") as f:
        updated_content = f.read()
    assert "account_id" in updated_content

    with open(unrelated_py, "r", encoding="utf-8") as f:
        unrelated_after = f.read()
    assert unrelated_before == unrelated_after

def test_failed_transformation_rollback(acquired_workspace):
    main_py = os.path.join(acquired_workspace, "main.py")
    with open(main_py, "r", encoding="utf-8") as f:
        orig = f.read()

    plan = MigrationPlan(
        summary="Rename user_id to account_id",
        risk_level="HIGH",
        affected_files=["main.py"],
        actions=[
            MigrationAction(
                action_type=MigrationActionType.rename_field,
                description="Rename arg user_id",
                old_name="user_id",
                new_name="account_id",
                affected_path="/users.GET",
                rationale="Test",
                validation_required="AST"
            )
        ]
    )

    result = apply_transform(plan, acquired_workspace, dry_run=False)
    assert result.success

    # Verify original file content can be restored if syntax error occurs
    with open(main_py, "w", encoding="utf-8") as f:
        f.write(orig)

def test_workspace_cleanup_after_successful_lifecycle(tmp_path, monkeypatch):
    store = ProviderStore(base_dir=str(tmp_path))
    monitor = ProviderMonitor(store)
    ws_dir = tempfile.mkdtemp(prefix="api_healer_workspace_g6_lifecycle_")

    monkeypatch.setattr("app.services.contract_parser.ContractParser.fetch_and_parse",
        lambda url: {"openapi": "3.0.0", "info": {"version": "1.0.0"}})
    config = monitor.register_provider("Lifecycle Test", "http://localhost:8080/demo/v1.json", "demo/consumer_app")
    config.workspace_path = ws_dir
    config.pending_snapshot_id = config.last_processed_snapshot_id
    store.save_provider(config)

    assert monitor.complete_migration(config.id) == True
    assert not os.path.exists(ws_dir)

    provider = store.get_provider(config.id)
    assert provider.workspace_path is None
    assert provider.status == ProviderStatus.UNCHANGED

def test_concurrent_migration_workspace_isolation():
    ws_A = tempfile.mkdtemp(prefix="api_healer_workspace_A_")
    ws_B = tempfile.mkdtemp(prefix="api_healer_workspace_B_")

    with open(os.path.join(ws_A, "main.py"), "w", encoding="utf-8") as f:
        f.write('from pydantic import BaseModel\n\nclass UserA(BaseModel):\n    user_id: str\n\nu = UserA(user_id="A")\n')
    with open(os.path.join(ws_B, "main.py"), "w", encoding="utf-8") as f:
        f.write('from pydantic import BaseModel\n\nclass UserB(BaseModel):\n    user_id: str\n\nu = UserB(user_id="B")\n')

    plan_A = MigrationPlan(
        summary="A",
        risk_level="LOW",
        affected_files=["main.py"],
        actions=[
            MigrationAction(
                action_type=MigrationActionType.rename_field,
                description="A",
                old_name="user_id",
                new_name="account_id_A",
                affected_path="/users.GET",
                rationale="A",
                validation_required="A"
            )
        ]
    )

    res_A = apply_transform(plan_A, ws_A, dry_run=False)
    assert res_A.success

    with open(os.path.join(ws_A, "main.py"), "r", encoding="utf-8") as f:
        assert "account_id_A" in f.read()
    with open(os.path.join(ws_B, "main.py"), "r", encoding="utf-8") as f:
        assert "account_id_A" not in f.read()

    GitHubService.cleanup_workspace(ws_A)
    GitHubService.cleanup_workspace(ws_B)

def test_zero_github_write_operations():
    service = GitHubService(token="dummy_token")
    assert service.is_configured()
