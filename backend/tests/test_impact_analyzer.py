import os
import pytest
from app.services.impact_analyzer import ImpactAnalyzer
from app.models.provider import EvidenceStrength
from app.models.diff_result import DiffResult, Change, ChangeType, ChangeSeverity

def test_impact_analyzer_strong_endpoint(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text('url = "/api/v1/users"')
    
    diff = DiffResult(changes=[
        Change(
            type=ChangeType.endpoint_removed,
            severity=ChangeSeverity.BREAKING,
            path="GET /api/v1/users",
            description="Removed"
        )
    ])
    
    analysis = ImpactAnalyzer.analyze(str(repo), diff)
    assert analysis.evidence_strength == EvidenceStrength.STRONG
    assert any("endpoint URL" in d for d in analysis.details)

def test_impact_analyzer_strong_kwarg(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text('user = User(user_id=123)')
    
    diff = DiffResult(changes=[
        Change(
            type=ChangeType.field_removed,
            severity=ChangeSeverity.BREAKING,
            path="User.properties.user_id",
            description="Removed"
        )
    ])
    
    analysis = ImpactAnalyzer.analyze(str(repo), diff)
    assert analysis.evidence_strength == EvidenceStrength.STRONG
    assert any("keyword argument" in d for d in analysis.details)

def test_impact_analyzer_weak_string(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text('logger.info("checking user_id")')
    
    diff = DiffResult(changes=[
        Change(
            type=ChangeType.field_removed,
            severity=ChangeSeverity.BREAKING,
            path="User.properties.user_id",
            description="Removed"
        )
    ])
    
    analysis = ImpactAnalyzer.analyze(str(repo), diff)
    assert analysis.evidence_strength == EvidenceStrength.WEAK
    assert any("Weak evidence: string literal" in d for d in analysis.details)

def test_impact_analyzer_none(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text('user = User(id=123)')
    
    diff = DiffResult(changes=[
        Change(
            type=ChangeType.field_removed,
            severity=ChangeSeverity.BREAKING,
            path="User.properties.user_id",
            description="Removed"
        )
    ])
    
    analysis = ImpactAnalyzer.analyze(str(repo), diff)
    assert analysis.evidence_strength == EvidenceStrength.NONE
