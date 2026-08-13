import logging
from typing import Any, Dict
from app.models.diff_result import DiffResult, ChangeType
from app.models.migration_plan import MigrationPlan, MigrationAction, MigrationActionType
from app.services.llm_provider import generate_plan_with_llm

logger = logging.getLogger(__name__)

def generate_fallback_plan(diff: DiffResult) -> MigrationPlan:
    """
    Deterministically translates a DiffResult into a MigrationPlan.
    This acts as a fallback when the LLM is unavailable or fails.
    """
    actions = []
    
    for change in diff.changes:
        if change.type == ChangeType.probable_rename:
            actions.append(MigrationAction(
                action_type=MigrationActionType.rename_field,
                description=f"Rename field {change.metadata.get('old_name')} to {change.metadata.get('new_name')}",
                old_name=change.metadata.get("old_name"),
                new_name=change.metadata.get("new_name"),
                affected_path=change.path,
                confidence=change.confidence,
                rationale="Fallback: Auto-detected probable rename.",
                validation_required="Update consumers referencing the old name to the new name."
            ))
        elif change.type in (ChangeType.field_removed, ChangeType.parameter_removed):
            actions.append(MigrationAction(
                action_type=MigrationActionType.remove_field,
                description=change.description,
                old_name=change.metadata.get("prop_name") or change.path.split(".")[-1],
                affected_path=change.path,
                rationale="Fallback: Field or parameter was removed.",
                validation_required="Remove usages of this field in the consumer codebase."
            ))
        elif change.type in (ChangeType.required_field_added, ChangeType.required_parameter_added, ChangeType.required_status_changed):
            actions.append(MigrationAction(
                action_type=MigrationActionType.add_required_field,
                description=change.description,
                new_name=change.metadata.get("prop_name") or change.path.split(".")[-1],
                affected_path=change.path,
                rationale="Fallback: A new required field or parameter was added.",
                validation_required="Update consumers to provide this required field."
            ))
        elif change.type in (ChangeType.endpoint_removed, ChangeType.method_removed, ChangeType.response_removed):
            actions.append(MigrationAction(
                action_type=MigrationActionType.review_required,
                description=change.description,
                affected_path=change.path,
                rationale="Fallback: Endpoint, method, or response was removed.",
                validation_required="Manual review required to handle the missing functionality."
            ))
        elif change.type in (ChangeType.endpoint_added, ChangeType.method_added):
            actions.append(MigrationAction(
                action_type=MigrationActionType.update_endpoint,
                description=change.description,
                affected_path=change.path,
                rationale="Fallback: New endpoint or method added.",
                validation_required="Consider integrating new endpoint/method if beneficial."
            ))
        elif change.type in (ChangeType.type_changed, ChangeType.parameter_type_changed, ChangeType.schema_changed):
            actions.append(MigrationAction(
                action_type=MigrationActionType.review_required,
                description=change.description,
                affected_path=change.path,
                rationale="Fallback: Type or schema changed.",
                validation_required="Review the API documentation to accommodate the new type."
            ))
        elif change.type in (ChangeType.field_added, ChangeType.parameter_added):
            actions.append(MigrationAction(
                action_type=MigrationActionType.review_required,
                description=change.description,
                affected_path=change.path,
                rationale="Fallback: Optional field or parameter added.",
                validation_required="Review if the new optional field/parameter should be utilized."
            ))
        else:
            actions.append(MigrationAction(
                action_type=MigrationActionType.review_required,
                description=change.description,
                affected_path=change.path,
                rationale="Fallback: General schema change.",
                validation_required="Review the API documentation for this path."
            ))
            
    return MigrationPlan(
        summary="Fallback deterministic migration plan.",
        risk_level="MEDIUM",
        actions=actions,
        affected_files=[],
        validation_steps=["Review all actions as they were generated deterministically without LLM assistance."]
    )

async def generate_migration_plan(diff: DiffResult, old_spec: Dict[str, Any], new_spec: Dict[str, Any]) -> MigrationPlan:
    """
    Attempts to generate a migration plan using the LLM. 
    Falls back to a deterministic planner on any failure.
    """
    try:
        return await generate_plan_with_llm(diff, old_spec, new_spec)
    except Exception as e:
        logger.warning(f"Failed to generate plan with LLM: {e}. Using fallback.")
        return generate_fallback_plan(diff)
