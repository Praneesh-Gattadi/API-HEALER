from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import datetime

class ProviderStatus(str, Enum):
    INITIALIZED = "INITIALIZED"
    UNCHANGED = "UNCHANGED"
    CHANGE_DETECTED = "CHANGE_DETECTED"
    MIGRATION_REQUIRED = "MIGRATION_REQUIRED"
    NO_MIGRATION_REQUIRED = "NO_MIGRATION_REQUIRED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CHECK_FAILED = "CHECK_FAILED"

class SnapshotStatus(str, Enum):
    OBSERVED = "OBSERVED"
    PROCESSED = "PROCESSED"
    PENDING_MIGRATION = "PENDING_MIGRATION"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"

class EvidenceStrength(str, Enum):
    STRONG = "STRONG"
    WEAK = "WEAK"
    NONE = "NONE"

class ImpactAnalysis(BaseModel):
    evidence_strength: EvidenceStrength = EvidenceStrength.NONE
    details: List[str] = Field(default_factory=list)

class ProviderSnapshot(BaseModel):
    id: str
    provider_id: str
    timestamp: str
    declared_contract_version: Optional[str] = None
    spec_hash: str
    spec_content_path: str
    changelog_content: Optional[str] = None
    status: SnapshotStatus = SnapshotStatus.OBSERVED

class ProviderConfig(BaseModel):
    id: str
    name: str
    spec_url: str
    changelog_url: Optional[str] = None
    repository_path: str
    declared_contract_version: Optional[str] = None
    status: ProviderStatus = ProviderStatus.INITIALIZED
    latest_seen_snapshot_id: Optional[str] = None
    last_processed_snapshot_id: Optional[str] = None
    pending_snapshot_id: Optional[str] = None

class MigrationDecision(BaseModel):
    status: ProviderStatus
    reason: str
    impact_analysis: Optional[ImpactAnalysis] = None
    diff_result: Optional[Any] = None  # Will be DiffResult but keeping Any to avoid circular dependency if not needed
