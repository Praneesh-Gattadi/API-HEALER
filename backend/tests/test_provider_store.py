import os
import shutil
import pytest
from app.models.provider import ProviderConfig, ProviderSnapshot, ProviderStatus, SnapshotStatus
from app.services.provider_store import ProviderStore

@pytest.fixture
def temp_store(tmp_path):
    store = ProviderStore(base_dir=str(tmp_path))
    yield store
    shutil.rmtree(tmp_path, ignore_errors=True)

def test_provider_store_lifecycle(temp_store):
    # 1. Create a provider
    config = ProviderConfig(
        id="test_provider_1",
        name="Test API",
        spec_url="https://api.example.com/openapi.json",
        repository_path="/test/repo"
    )
    temp_store.save_provider(config)
    
    # 2. Retrieve provider
    retrieved = temp_store.get_provider("test_provider_1")
    assert retrieved is not None
    assert retrieved.name == "Test API"
    assert retrieved.status == ProviderStatus.INITIALIZED
    
    # 3. Create a snapshot
    snapshot = ProviderSnapshot(
        id="snap_v1",
        provider_id="test_provider_1",
        timestamp="2026-08-13T00:00:00Z",
        spec_hash="abc123hash",
        spec_content_path="", # Will be set by save
        status=SnapshotStatus.OBSERVED
    )
    temp_store.save_snapshot(snapshot, {"openapi": "3.0.0"})
    
    # 4. Retrieve snapshot
    retrieved_snap = temp_store.get_snapshot("test_provider_1", "snap_v1")
    assert retrieved_snap is not None
    assert retrieved_snap.spec_hash == "abc123hash"
    assert retrieved_snap.spec_content_path.endswith("snap_v1_spec.json")
    
    # 5. Retrieve spec content
    spec = temp_store.get_spec_content("test_provider_1", "snap_v1")
    assert spec is not None
    assert spec["openapi"] == "3.0.0"

    # 6. List providers
    providers = temp_store.list_providers()
    assert len(providers) == 1
    assert providers[0].id == "test_provider_1"
