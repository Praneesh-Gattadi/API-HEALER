from app.models.provider import MigrationDecision, ProviderStatus, ImpactAnalysis, EvidenceStrength
from app.models.diff_result import DiffResult, ChangeSeverity

class DecisionEngine:
    @classmethod
    def evaluate(cls, diff_result: DiffResult, impact_analysis: ImpactAnalysis, changelog_content: str = None) -> MigrationDecision:
        has_breaking = any(c.severity == ChangeSeverity.BREAKING for c in diff_result.changes)
        
        # Semantic discrepancy heuristic
        has_semantic_claim = False
        if changelog_content:
            lower_log = changelog_content.lower()
            if "breaking" in lower_log or "behavior changed" in lower_log or "deprecated" in lower_log or "removed" in lower_log:
                has_semantic_claim = True
                
        # No structural changes
        if not diff_result.changes:
            if has_semantic_claim:
                return MigrationDecision(
                    status=ProviderStatus.REVIEW_REQUIRED,
                    reason="Changelog describes a semantic change not visible in the structural OpenAPI diff.",
                    diff_result=diff_result,
                    impact_analysis=impact_analysis
                )
            return MigrationDecision(status=ProviderStatus.UNCHANGED, reason="No structural changes detected.", diff_result=diff_result, impact_analysis=impact_analysis)

        # Evaluate impact
        if impact_analysis.evidence_strength == EvidenceStrength.STRONG:
            if has_breaking:
                reason = "Breaking structural changes detected and confirmed by changelog." if has_semantic_claim else "Breaking changes detected that directly impact your codebase."
                return MigrationDecision(
                    status=ProviderStatus.MIGRATION_REQUIRED, 
                    reason=reason, 
                    diff_result=diff_result, 
                    impact_analysis=impact_analysis
                )
            else:
                if has_semantic_claim:
                    return MigrationDecision(
                        status=ProviderStatus.REVIEW_REQUIRED,
                        reason="Changelog claims breaking changes but structural diff is non-breaking.",
                        diff_result=diff_result,
                        impact_analysis=impact_analysis
                    )
                return MigrationDecision(
                    status=ProviderStatus.NO_MIGRATION_REQUIRED, 
                    reason="Changes detected are non-breaking. No automated migration needed.", 
                    diff_result=diff_result, 
                    impact_analysis=impact_analysis
                )
                
        elif impact_analysis.evidence_strength == EvidenceStrength.WEAK:
            return MigrationDecision(
                status=ProviderStatus.REVIEW_REQUIRED, 
                reason="Weak evidence of API usage found. Manual review required to determine impact.", 
                diff_result=diff_result, 
                impact_analysis=impact_analysis
            )
            
        else:
            # NONE
            if has_breaking:
                return MigrationDecision(
                    status=ProviderStatus.NO_MIGRATION_REQUIRED, 
                    reason="Breaking changes detected, but they do not appear to be used in your codebase.", 
                    diff_result=diff_result, 
                    impact_analysis=impact_analysis
                )
            else:
                if has_semantic_claim:
                    return MigrationDecision(
                        status=ProviderStatus.NO_MIGRATION_REQUIRED, 
                        reason="Semantic changes detected, but no consumer impact.", 
                        diff_result=diff_result, 
                        impact_analysis=impact_analysis
                    )
                return MigrationDecision(
                    status=ProviderStatus.NO_MIGRATION_REQUIRED, 
                    reason="Non-breaking changes detected with no consumer impact.", 
                    diff_result=diff_result, 
                    impact_analysis=impact_analysis
                )
