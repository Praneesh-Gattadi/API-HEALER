import pytest
from app.services.provider_monitor import ProviderMonitor
from app.services.provider_store import ProviderStore
from app.models.provider import ProviderStatus, SnapshotStatus

@pytest.fixture
def monitor(tmp_path):
    store = ProviderStore(base_dir=str(tmp_path))
    return ProviderMonitor(store)

def test_register_provider_creates_baseline(monitor, monkeypatch):
    monkeypatch.setattr("app.services.contract_parser.ContractParser.fetch_and_parse", lambda url: {"openapi": "3.0.0", "info": {"version": "1.0.0"}})
    
    config = monitor.register_provider("Test", "http://test", "/repo")
    
    assert config.status == ProviderStatus.INITIALIZED
    assert config.declared_contract_version == "1.0.0"
    assert config.last_processed_snapshot_id == config.latest_seen_snapshot_id
    assert config.pending_snapshot_id is None
    
    snapshot = monitor.store.get_snapshot(config.id, config.last_processed_snapshot_id)
    assert snapshot.status == SnapshotStatus.PROCESSED

@pytest.mark.asyncio
async def test_check_unchanged(monitor, monkeypatch):
    monkeypatch.setattr("app.services.contract_parser.ContractParser.fetch_and_parse", lambda url: {"openapi": "3.0.0", "info": {"version": "1.0.0"}})
    config = monitor.register_provider("Test", "http://test", "/repo")
    
    decision = await monitor.check_for_updates(config.id)
    assert decision.status == ProviderStatus.UNCHANGED
    
    provider = monitor.store.get_provider(config.id)
    assert provider.status == ProviderStatus.UNCHANGED

@pytest.mark.asyncio
async def test_check_breaking_strong_impact(monitor, monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text('url = "/api/v1/users"')
    
    monkeypatch.setattr("app.services.contract_parser.ContractParser.fetch_and_parse", 
        lambda url: {
            "openapi": "3.0.0", 
            "paths": {"/api/v1/users": {"get": {"responses": {"200": {"description": "OK"}}}}}
        })
    config = monitor.register_provider("Test", "http://test", str(repo))
    v1_id = config.last_processed_snapshot_id
    
    monkeypatch.setattr("app.services.contract_parser.ContractParser.fetch_and_parse", 
        lambda url: {
            "openapi": "3.0.0", 
            "paths": {}
        })
    
    decision = await monitor.check_for_updates(config.id)
    
    assert decision.status == ProviderStatus.MIGRATION_REQUIRED
    
    provider = monitor.store.get_provider(config.id)
    assert provider.status == ProviderStatus.MIGRATION_REQUIRED
    assert provider.last_processed_snapshot_id == v1_id
    assert provider.pending_snapshot_id is not None
    assert provider.pending_snapshot_id != v1_id
    
    pending_snap = monitor.store.get_snapshot(config.id, provider.pending_snapshot_id)
    assert pending_snap.status == SnapshotStatus.PENDING_MIGRATION
    
    assert monitor.complete_migration(config.id) == True
    provider = monitor.store.get_provider(config.id)
    assert provider.status == ProviderStatus.UNCHANGED
    assert provider.last_processed_snapshot_id == pending_snap.id
    assert provider.pending_snapshot_id is None
    
    processed_snap = monitor.store.get_snapshot(config.id, pending_snap.id)
    assert processed_snap.status == SnapshotStatus.PROCESSED

@pytest.mark.asyncio
async def test_pending_migration_repeated_checks(monitor, monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text('url = "/api/v1/users"')
    
    monkeypatch.setattr("app.services.contract_parser.ContractParser.fetch_and_parse", 
        lambda url: {"openapi": "3.0.0", "paths": {"/api/v1/users": {"get": {}}}})
    config = monitor.register_provider("Test", "http://test", str(repo))
    v1_id = config.last_processed_snapshot_id
    
    monkeypatch.setattr("app.services.contract_parser.ContractParser.fetch_and_parse", 
        lambda url: {"openapi": "3.0.0", "paths": {}})
    
    decision1 = await monitor.check_for_updates(config.id)
    assert decision1.status == ProviderStatus.MIGRATION_REQUIRED
    
    provider1 = monitor.store.get_provider(config.id)
    v2_id = provider1.pending_snapshot_id
    
    decision2 = await monitor.check_for_updates(config.id)
    assert decision2.status == ProviderStatus.MIGRATION_REQUIRED
    
    provider2 = monitor.store.get_provider(config.id)
    assert provider2.status == ProviderStatus.MIGRATION_REQUIRED
    assert provider2.last_processed_snapshot_id == v1_id
    assert provider2.pending_snapshot_id == v2_id
    assert provider2.latest_seen_snapshot_id == v2_id
