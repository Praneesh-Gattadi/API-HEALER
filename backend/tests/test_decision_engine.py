import pytest
from app.models.provider import ProviderStatus, EvidenceStrength, SnapshotStatus
from app.models.diff_result import DiffResult, Change, ChangeType, ChangeSeverity
from app.services.decision_engine import DecisionEngine
from app.models.provider import ImpactAnalysis

def test_decision_engine_strong_breaking():
    diff = DiffResult(changes=[Change(type=ChangeType.endpoint_removed, severity=ChangeSeverity.BREAKING, path="/users", description="")])
    impact = ImpactAnalysis(evidence_strength=EvidenceStrength.STRONG, details=[])
    
    decision = DecisionEngine.evaluate(diff, impact)
    assert decision.status == ProviderStatus.MIGRATION_REQUIRED

def test_decision_engine_weak_breaking():
    diff = DiffResult(changes=[Change(type=ChangeType.endpoint_removed, severity=ChangeSeverity.BREAKING, path="/users", description="")])
    impact = ImpactAnalysis(evidence_strength=EvidenceStrength.WEAK, details=[])
    
    decision = DecisionEngine.evaluate(diff, impact)
    assert decision.status == ProviderStatus.REVIEW_REQUIRED

def test_decision_engine_none_breaking():
    diff = DiffResult(changes=[Change(type=ChangeType.endpoint_removed, severity=ChangeSeverity.BREAKING, path="/users", description="")])
    impact = ImpactAnalysis(evidence_strength=EvidenceStrength.NONE, details=[])
    
    decision = DecisionEngine.evaluate(diff, impact)
    assert decision.status == ProviderStatus.NO_MIGRATION_REQUIRED

def test_decision_engine_strong_nonbreaking():
    diff = DiffResult(changes=[Change(type=ChangeType.endpoint_added, severity=ChangeSeverity.INFO, path="/users", description="")])
    impact = ImpactAnalysis(evidence_strength=EvidenceStrength.STRONG, details=[])
    
    decision = DecisionEngine.evaluate(diff, impact)
    decision = DecisionEngine.evaluate(diff, impact)
    assert decision.status == ProviderStatus.NO_MIGRATION_REQUIRED

def test_decision_engine_changelog_agrees_breaking():
    diff = DiffResult(changes=[Change(type=ChangeType.endpoint_removed, severity=ChangeSeverity.BREAKING, path="/users", description="")])
    impact = ImpactAnalysis(evidence_strength=EvidenceStrength.STRONG, details=[])
    decision = DecisionEngine.evaluate(diff, impact, "Breaking change: Removed /users")
    assert decision.status == ProviderStatus.MIGRATION_REQUIRED

def test_decision_engine_changelog_contradicts_structural_diff():
    # Structural diff is INFO, but changelog claims breaking
    diff = DiffResult(changes=[Change(type=ChangeType.endpoint_added, severity=ChangeSeverity.INFO, path="/users", description="")])
    impact = ImpactAnalysis(evidence_strength=EvidenceStrength.STRONG, details=[])
    decision = DecisionEngine.evaluate(diff, impact, "Breaking change: updated /users")
    assert decision.status == ProviderStatus.REVIEW_REQUIRED

def test_decision_engine_changelog_semantic_only():
    # No structural diff, but changelog claims breaking
    diff = DiffResult(changes=[])
    impact = ImpactAnalysis(evidence_strength=EvidenceStrength.NONE, details=[])
    decision = DecisionEngine.evaluate(diff, impact, "Behavior changed for /users")
    assert decision.status == ProviderStatus.REVIEW_REQUIRED

def test_decision_engine_empty_changelog():
    diff = DiffResult(changes=[Change(type=ChangeType.endpoint_added, severity=ChangeSeverity.INFO, path="/users", description="")])
    impact = ImpactAnalysis(evidence_strength=EvidenceStrength.STRONG, details=[])
    decision = DecisionEngine.evaluate(diff, impact, "")
    assert decision.status == ProviderStatus.NO_MIGRATION_REQUIRED
