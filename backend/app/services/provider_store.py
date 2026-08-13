import json
import os
from typing import List, Optional
from app.models.provider import ProviderConfig, ProviderSnapshot

class ProviderStore:
    def __init__(self, base_dir: str = ".api_healer_data"):
        self.base_dir = base_dir
        self.providers_file = os.path.join(base_dir, "providers.json")
        self.snapshots_dir = os.path.join(base_dir, "snapshots")
        self._ensure_dirs()

    def _ensure_dirs(self):
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.snapshots_dir, exist_ok=True)
        if not os.path.exists(self.providers_file):
            with open(self.providers_file, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def _read_providers(self) -> List[ProviderConfig]:
        if not os.path.exists(self.providers_file):
            return []
        try:
            with open(self.providers_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [ProviderConfig(**p) for p in data]
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_providers(self, providers: List[ProviderConfig]):
        with open(self.providers_file, 'w', encoding='utf-8') as f:
            json.dump([p.model_dump() for p in providers], f, indent=2)

    def list_providers(self) -> List[ProviderConfig]:
        return self._read_providers()

    def get_provider(self, provider_id: str) -> Optional[ProviderConfig]:
        for p in self._read_providers():
            if p.id == provider_id:
                return p
        return None

    def save_provider(self, provider: ProviderConfig):
        providers = self._read_providers()
        updated = False
        for i, p in enumerate(providers):
            if p.id == provider.id:
                providers[i] = provider
                updated = True
                break
        if not updated:
            providers.append(provider)
        self._write_providers(providers)

    def get_snapshot(self, provider_id: str, snapshot_id: str) -> Optional[ProviderSnapshot]:
        provider_snapshots_dir = os.path.join(self.snapshots_dir, provider_id)
        snapshot_file = os.path.join(provider_snapshots_dir, f"{snapshot_id}.json")
        if not os.path.exists(snapshot_file):
            return None
        try:
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return ProviderSnapshot(**data)
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    def save_snapshot(self, snapshot: ProviderSnapshot, spec_content: dict):
        provider_snapshots_dir = os.path.join(self.snapshots_dir, snapshot.provider_id)
        os.makedirs(provider_snapshots_dir, exist_ok=True)
        
        # Save the snapshot metadata
        snapshot_file = os.path.join(provider_snapshots_dir, f"{snapshot.id}.json")
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot.model_dump(), f, indent=2)
            
        # Save the actual spec content
        spec_file = os.path.join(provider_snapshots_dir, f"{snapshot.id}_spec.json")
        with open(spec_file, 'w', encoding='utf-8') as f:
            json.dump(spec_content, f, indent=2)
            
        snapshot.spec_content_path = spec_file
        # Update the metadata with the correct path
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot.model_dump(), f, indent=2)

    def _update_snapshot_metadata_only(self, snapshot: ProviderSnapshot):
        provider_snapshots_dir = os.path.join(self.snapshots_dir, snapshot.provider_id)
        snapshot_file = os.path.join(provider_snapshots_dir, f"{snapshot.id}.json")
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot.model_dump(), f, indent=2)

    def get_spec_content(self, provider_id: str, snapshot_id: str) -> Optional[dict]:
        provider_snapshots_dir = os.path.join(self.snapshots_dir, provider_id)
        spec_file = os.path.join(provider_snapshots_dir, f"{snapshot_id}_spec.json")
        if not os.path.exists(spec_file):
            return None
        try:
            with open(spec_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None
