import os
from fastapi import APIRouter, HTTPException
from app.models.transformation_result import TransformRequest, TransformationResult
from app.services.code_transformer import apply_transform
from app.services.provider_store import ProviderStore
from app.services.provider_monitor import ProviderMonitor

router = APIRouter()

@router.post("", response_model=TransformationResult)
def execute_transform(request: TransformRequest):
    try:
        target_root = request.repository_root
        if request.provider_id:
            store = ProviderStore()
            provider = store.get_provider(request.provider_id)
            if provider and provider.workspace_path and os.path.exists(provider.workspace_path):
                target_root = provider.workspace_path

        result = apply_transform(
            request.migration_plan,
            target_root,
            request.dry_run
        )
        
        # Verify and complete provider migration if applicable
        if request.provider_id and not request.dry_run and result.success:
            monitor = ProviderMonitor(ProviderStore())
            monitor.complete_migration(request.provider_id)
            
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transformation error: {str(e)}")
