import os
import hashlib
import datetime
import uuid
from app.models.provider import ProviderConfig, ProviderSnapshot, SnapshotStatus, ProviderStatus, MigrationDecision
from app.services.provider_store import ProviderStore
from app.services.contract_parser import ContractParser
from app.services.openapi_diff import compare_openapi_specs
from app.services.impact_analyzer import ImpactAnalyzer
from app.services.decision_engine import DecisionEngine

class ProviderMonitor:
    def __init__(self, store: ProviderStore):
        self.store = store

    def _hash_content(self, content_dict: dict) -> str:
        import json
        content_str = json.dumps(content_dict, sort_keys=True)
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()

    def register_provider(self, name: str, spec_url: str, repository_path: str, changelog_url: str = None, github_repo: str = None) -> ProviderConfig:
        provider_id = str(uuid.uuid4())
        
        # 1. Fetch initial contract
        spec_content = ContractParser.fetch_and_parse(spec_url)
        spec_hash = self._hash_content(spec_content)
        
        # Extract declared version if available
        declared_version = spec_content.get("info", {}).get("version")
        
        # 2. Create snapshot
        snapshot_id = f"snap_{uuid.uuid4().hex[:8]}"
        snapshot = ProviderSnapshot(
            id=snapshot_id,
            provider_id=provider_id,
            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            declared_contract_version=declared_version,
            spec_hash=spec_hash,
            spec_content_path="",
            status=SnapshotStatus.PROCESSED  # Baseline is processed
        )
        
        self.store.save_snapshot(snapshot, spec_content)
        
        # 3. Create config
        config = ProviderConfig(
            id=provider_id,
            name=name,
            spec_url=spec_url,
            changelog_url=changelog_url,
            repository_path=repository_path,
            github_repo=github_repo,
            workspace_path=None,
            declared_contract_version=declared_version,
            status=ProviderStatus.INITIALIZED,
            latest_seen_snapshot_id=snapshot_id,
            last_processed_snapshot_id=snapshot_id,
            pending_snapshot_id=None
        )
        self.store.save_provider(config)
        return config

    async def check_for_updates(self, provider_id: str) -> MigrationDecision:
        provider = self.store.get_provider(provider_id)
        if not provider:
            raise ValueError(f"Provider {provider_id} not found")
            
        # 1. Fetch new contract
        try:
            new_spec = ContractParser.fetch_and_parse(provider.spec_url)
            new_hash = self._hash_content(new_spec)
        except Exception as e:
            provider.status = ProviderStatus.CHECK_FAILED
            self.store.save_provider(provider)
            return MigrationDecision(status=ProviderStatus.CHECK_FAILED, reason=str(e))
            
        latest_seen_snapshot = self.store.get_snapshot(provider_id, provider.latest_seen_snapshot_id)
        
        # 2. Compare hash
        if latest_seen_snapshot and latest_seen_snapshot.spec_hash == new_hash:
            if provider.status in (ProviderStatus.MIGRATION_REQUIRED, ProviderStatus.REVIEW_REQUIRED):
                return MigrationDecision(
                    status=provider.status, 
                    reason="A migration is already pending for this API specification."
                )
            provider.status = ProviderStatus.UNCHANGED
            self.store.save_provider(provider)
            return MigrationDecision(status=ProviderStatus.UNCHANGED, reason="No changes detected in the API specification.")
            
        # 3. Change detected, create new snapshot
        declared_version = new_spec.get("info", {}).get("version")
        snapshot_id = f"snap_{uuid.uuid4().hex[:8]}"
        snapshot = ProviderSnapshot(
            id=snapshot_id,
            provider_id=provider_id,
            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            declared_contract_version=declared_version,
            spec_hash=new_hash,
            spec_content_path="",
            status=SnapshotStatus.OBSERVED
        )
        self.store.save_snapshot(snapshot, new_spec)
        
        # Update latest seen
        provider.latest_seen_snapshot_id = snapshot_id
        
        # 4. Compare with last PROCESSED snapshot
        old_spec = self.store.get_spec_content(provider_id, provider.last_processed_snapshot_id)
        if not old_spec:
            old_spec = new_spec
            
        diff_result = compare_openapi_specs(old_spec, new_spec)
        
        # 5. Fetch Changelog
        changelog_content = None
        if provider.changelog_url:
            try:
                changelog_content = ContractParser.fetch_text(provider.changelog_url)
            except Exception:
                pass
                
        # 6. Resolve Target Repository Path (Local or GitHub Acquired Workspace)
        target_repo_path = provider.workspace_path or provider.repository_path

        if provider.github_repo and (not target_repo_path or not os.path.exists(target_repo_path)):
            from app.services.github_service import GitHubService
            gh_service = GitHubService()
            if gh_service.is_configured():
                acq_result = await gh_service.acquire_repository(provider.github_repo)
                if acq_result.success:
                    provider.workspace_path = acq_result.workspace_path
                    target_repo_path = acq_result.workspace_path
                    self.store.save_provider(provider)

        # 7. Impact Analysis
        impact = ImpactAnalyzer.analyze(target_repo_path, diff_result)
        
        # 8. Decision Engine
        decision = DecisionEngine.evaluate(diff_result, impact, changelog_content)
        
        provider.status = decision.status
        
        if decision.status == ProviderStatus.MIGRATION_REQUIRED:
            snapshot.status = SnapshotStatus.PENDING_MIGRATION
            self.store.save_snapshot(snapshot, new_spec)
            provider.pending_snapshot_id = snapshot_id
        elif decision.status == ProviderStatus.REVIEW_REQUIRED:
            snapshot.status = SnapshotStatus.REVIEW_REQUIRED
            self.store.save_snapshot(snapshot, new_spec)
            provider.pending_snapshot_id = snapshot_id
        elif decision.status == ProviderStatus.NO_MIGRATION_REQUIRED:
            if provider.workspace_path:
                from app.services.github_service import GitHubService
                GitHubService.cleanup_workspace(provider.workspace_path)
                provider.workspace_path = None
            
        self.store.save_provider(provider)
        return decision

    def complete_migration(self, provider_id: str) -> bool:
        provider = self.store.get_provider(provider_id)
        if not provider or not provider.pending_snapshot_id:
            return False

        if provider.workspace_path:
            from app.services.github_service import GitHubService
            GitHubService.cleanup_workspace(provider.workspace_path)
            provider.workspace_path = None
            
        # Transition pending -> processed
        pending_snap = self.store.get_snapshot(provider_id, provider.pending_snapshot_id)
        if pending_snap:
            pending_snap.status = SnapshotStatus.PROCESSED
            self.store._update_snapshot_metadata_only(pending_snap)
            
        provider.last_processed_snapshot_id = provider.pending_snapshot_id
        provider.pending_snapshot_id = None
        provider.status = ProviderStatus.UNCHANGED
        self.store.save_provider(provider)
        return True
