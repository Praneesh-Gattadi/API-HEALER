from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from app.models.provider import ProviderConfig, MigrationDecision
from app.services.provider_store import ProviderStore
from app.services.provider_monitor import ProviderMonitor

router = APIRouter()

def get_monitor() -> ProviderMonitor:
    store = ProviderStore()
    return ProviderMonitor(store)

class RegisterProviderRequest(BaseModel):
    name: str
    spec_url: str
    changelog_url: Optional[str] = None
    repository_path: str

@router.post("", response_model=ProviderConfig)
async def register_provider(req: RegisterProviderRequest, monitor: ProviderMonitor = Depends(get_monitor)):
    try:
        config = monitor.register_provider(req.name, req.spec_url, req.repository_path, req.changelog_url)
        return config
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=List[ProviderConfig])
async def list_providers(monitor: ProviderMonitor = Depends(get_monitor)):
    return monitor.store.list_providers()

@router.get("/{provider_id}", response_model=ProviderConfig)
async def get_provider(provider_id: str, monitor: ProviderMonitor = Depends(get_monitor)):
    provider = monitor.store.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider

@router.post("/{provider_id}/check", response_model=MigrationDecision)
async def check_provider_updates(provider_id: str, monitor: ProviderMonitor = Depends(get_monitor)):
    try:
        decision = monitor.check_for_updates(provider_id)
        return decision
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{provider_id}/snapshots/{snapshot_id}")
async def get_snapshot_spec(provider_id: str, snapshot_id: str, monitor: ProviderMonitor = Depends(get_monitor)):
    content = monitor.store.get_spec_content(provider_id, snapshot_id)
    if not content:
        raise HTTPException(status_code=404, detail="Snapshot spec not found")
    return content
