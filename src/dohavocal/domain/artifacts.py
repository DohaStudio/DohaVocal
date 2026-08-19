"""Immutable metadata contracts for derived Vocal artifacts."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ArtifactLineage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_asset_version_id: str
    parent_asset_version_id: str
    processing_chain_id: str
    provider_id: str
    model_manifest_id: str
    settings_snapshot: dict[str, Any]
    processing_types: tuple[str, ...]
    created_at: datetime
    checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    checksum_scope: Literal["metadata_descriptor"] = "metadata_descriptor"
    source_artifact_id: str | None = None
    parent_artifact_id: str | None = None
    job_id: str


class VocalArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_id: str
    artifact_kind: Literal["audio", "analysis"]
    media_type: str
    size_bytes: int = Field(ge=0)
    checksum_algorithm: Literal["sha256"] = "sha256"
    artifact_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    checksum_scope: Literal["metadata_descriptor"] = "metadata_descriptor"
    payload_present: Literal[False] = False
    producer_type: Literal["provider"] = "provider"
    producer_id: str
    run_id: str
    retention_status: Literal["candidate"] = "candidate"
    output_asset_version_id: str
    lineage: ArtifactLineage
    analysis_result: dict[str, Any] | None = None
