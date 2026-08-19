"""Immutable Model Manifest contract with DohaVocal extensions."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from dohavocal.domain.jobs import JobType

ReviewStatus = Literal["UNKNOWN", "REVIEW_REQUIRED", "APPROVED", "REJECTED"]


class ModelManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model_manifest_id: str
    provider_id: str
    model_id: str
    model_version: str
    checkpoint_version: str
    model_type: str
    capabilities: tuple[JobType, ...]
    input_formats: tuple[str, ...]
    output_formats: tuple[str, ...]
    api_contract_version: str
    dataset_manifest_id: str | None = None
    training_run_id: str | None = None
    evaluation_result_id: str | None = None
    license_status: ReviewStatus
    commercial_usage_status: ReviewStatus
    recommended_vram: None = None
    runtime_environment: dict[str, str]
    artifact_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_checksum_scope: Literal["fake_manifest_descriptor"] = (
        "fake_manifest_descriptor"
    )
    created_at: datetime
    voice_identity_scope: Literal["generic"] = "generic"
    consent_requirement: Literal["caller_verified"] = "caller_verified"
    supported_languages: tuple[str, ...] = ()
    supported_vocal_styles: tuple[str, ...] = ()
