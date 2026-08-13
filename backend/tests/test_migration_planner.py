import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock

from app.models.diff_result import DiffResult, Change, ChangeType, ChangeSeverity
from app.models.migration_plan import MigrationActionType
from app.services.migration_planner import generate_fallback_plan, generate_migration_plan

@pytest.fixture
def sample_diff_result():
    return DiffResult(changes=[
        Change(
            type=ChangeType.probable_rename,
            severity=ChangeSeverity.WARNING,
            path="/users",
            description="Probable rename",
            metadata={"old_name": "user_id", "new_name": "id"}
        )
    ])

def test_probable_rename_fallback():
    diff = DiffResult(changes=[
        Change(
            type=ChangeType.probable_rename,
            severity=ChangeSeverity.WARNING,
            path="/users",
            description="Probable rename",
            metadata={"old_name": "user_id", "new_name": "id"}
        )
    ])
    plan = generate_fallback_plan(diff)
    assert len(plan.actions) == 1
    assert plan.actions[0].action_type == MigrationActionType.rename_field
    assert plan.actions[0].old_name == "user_id"
    assert plan.actions[0].new_name == "id"

def test_field_removal_fallback():
    diff = DiffResult(changes=[
        Change(
            type=ChangeType.field_removed,
            severity=ChangeSeverity.BREAKING,
            path="/users.GET.responses.200.content.application/json.schema.properties.name",
            description="Field name removed",
            metadata={"prop_name": "name"}
        )
    ])
    plan = generate_fallback_plan(diff)
    assert len(plan.actions) == 1
    assert plan.actions[0].action_type == MigrationActionType.remove_field
    assert plan.actions[0].old_name == "name"

def test_required_field_addition_fallback():
    diff = DiffResult(changes=[
        Change(
            type=ChangeType.required_field_added,
            severity=ChangeSeverity.BREAKING,
            path="/users.POST.requestBody.content.application/json.schema.properties.email",
            description="Required field email added",
            metadata={"prop_name": "email"}
        )
    ])
    plan = generate_fallback_plan(diff)
    assert len(plan.actions) == 1
    assert plan.actions[0].action_type == MigrationActionType.add_required_field
    assert plan.actions[0].new_name == "email"

def test_endpoint_removal_fallback():
    diff = DiffResult(changes=[
        Change(
            type=ChangeType.endpoint_removed,
            severity=ChangeSeverity.BREAKING,
            path="/posts",
            description="Endpoint /posts removed"
        )
    ])
    plan = generate_fallback_plan(diff)
    assert len(plan.actions) == 1
    assert plan.actions[0].action_type == MigrationActionType.review_required
    assert plan.actions[0].affected_path == "/posts"

def test_multiple_changes_fallback():
    diff = DiffResult(changes=[
        Change(
            type=ChangeType.endpoint_removed,
            severity=ChangeSeverity.BREAKING,
            path="/posts",
            description="Endpoint /posts removed"
        ),
        Change(
            type=ChangeType.probable_rename,
            severity=ChangeSeverity.WARNING,
            path="/users",
            description="Probable rename",
            metadata={"old_name": "user_id", "new_name": "id"}
        )
    ])
    plan = generate_fallback_plan(diff)
    assert len(plan.actions) == 2
    assert plan.actions[0].action_type == MigrationActionType.review_required
    assert plan.actions[1].action_type == MigrationActionType.rename_field

@pytest.mark.asyncio
@patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"})
@patch("app.services.llm_provider.get_client")
async def test_llm_success(mock_get_client, sample_diff_result):
    mock_client = MagicMock()
    mock_response = MagicMock()
    
    mock_response.text = '{"summary": "Test", "risk_level": "LOW", "actions": [{"action_type": "rename_field", "description": "test", "old_name": "user_id", "new_name": "id", "affected_path": "/users", "confidence": 0.9, "rationale": "test", "validation_required": "test"}], "affected_files": [], "validation_steps": []}'
    
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client
    
    plan = await generate_migration_plan(sample_diff_result, {}, {})
    assert plan.summary == "Test"
    assert len(plan.actions) == 1
    assert plan.actions[0].action_type == MigrationActionType.rename_field
    
@pytest.mark.asyncio
@patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"})
@patch("app.services.llm_provider.get_client")
async def test_llm_failure_invalid_json(mock_get_client, sample_diff_result):
    mock_client = MagicMock()
    mock_response = MagicMock()
    
    mock_response.text = 'invalid json'
    
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client
    
    plan = await generate_migration_plan(sample_diff_result, {}, {})
    assert plan.summary == "Fallback deterministic migration plan."
    
@pytest.mark.asyncio
@patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"})
@patch("app.services.llm_provider.get_client")
async def test_llm_failure_exception(mock_get_client, sample_diff_result):
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=Exception("API Error"))
    mock_get_client.return_value = mock_client
    
    plan = await generate_migration_plan(sample_diff_result, {}, {})
    assert plan.summary == "Fallback deterministic migration plan."

@pytest.mark.asyncio
@patch.dict(os.environ, clear=True)
async def test_gemini_unavailable_no_api_key_fallback(sample_diff_result):
    plan = await generate_migration_plan(sample_diff_result, {}, {})
    assert plan.summary == "Fallback deterministic migration plan."

def test_field_added_fallback():
    diff = DiffResult(changes=[Change(type=ChangeType.field_added, severity=ChangeSeverity.INFO, path="/x", description="x")])
    plan = generate_fallback_plan(diff)
    assert plan.actions[0].action_type == MigrationActionType.review_required

def test_type_changed_fallback():
    diff = DiffResult(changes=[Change(type=ChangeType.type_changed, severity=ChangeSeverity.BREAKING, path="/x", description="x")])
    plan = generate_fallback_plan(diff)
    assert plan.actions[0].action_type == MigrationActionType.review_required

def test_endpoint_added_fallback():
    diff = DiffResult(changes=[Change(type=ChangeType.endpoint_added, severity=ChangeSeverity.INFO, path="/x", description="x")])
    plan = generate_fallback_plan(diff)
    assert plan.actions[0].action_type == MigrationActionType.update_endpoint

def test_method_added_fallback():
    diff = DiffResult(changes=[Change(type=ChangeType.method_added, severity=ChangeSeverity.INFO, path="/x", description="x")])
    plan = generate_fallback_plan(diff)
    assert plan.actions[0].action_type == MigrationActionType.update_endpoint

def test_response_removed_fallback():
    diff = DiffResult(changes=[Change(type=ChangeType.response_removed, severity=ChangeSeverity.BREAKING, path="/x", description="x")])
    plan = generate_fallback_plan(diff)
    assert plan.actions[0].action_type == MigrationActionType.review_required

def test_parameter_removed_fallback():
    diff = DiffResult(changes=[Change(type=ChangeType.parameter_removed, severity=ChangeSeverity.BREAKING, path="/x", description="x")])
    plan = generate_fallback_plan(diff)
    assert plan.actions[0].action_type == MigrationActionType.remove_field

def test_parameter_added_fallback():
    diff = DiffResult(changes=[Change(type=ChangeType.parameter_added, severity=ChangeSeverity.INFO, path="/x", description="x")])
    plan = generate_fallback_plan(diff)
    assert plan.actions[0].action_type == MigrationActionType.review_required

def test_parameter_type_changed_fallback():
    diff = DiffResult(changes=[Change(type=ChangeType.parameter_type_changed, severity=ChangeSeverity.BREAKING, path="/x", description="x")])
    plan = generate_fallback_plan(diff)
    assert plan.actions[0].action_type == MigrationActionType.review_required
