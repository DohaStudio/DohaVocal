"""Common and capability-specific Vocal Job contracts."""

import re
from copy import deepcopy
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from dohavocal.domain.errors import ErrorDetail


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(StrEnum):
    VOCAL_GENERATION = "vocal_generation"
    VOICE_CONVERSION = "voice_conversion"
    VOCAL_CORRECTION = "vocal_correction"
    VOCAL_ANALYSIS = "vocal_analysis"


class CorrectionType(StrEnum):
    PITCH = "pitch_correction"
    TIMING = "timing_correction"
    NOISE_REDUCTION = "noise_reduction"
    BREATH_CLEANUP = "breath_cleanup"
    SILENCE_CLEANUP = "silence_cleanup"
    NATURAL_TUNE = "natural_tune"
    STRONG_AUTOTUNE = "strong_autotune"
    NORMALIZATION = "normalization"
    DE_ESSER = "de_esser"
    EQ = "eq"
    COMPRESSION = "compression"


class AnalysisType(StrEnum):
    PITCH = "pitch"
    TIMING = "timing"
    PRONUNCIATION = "pronunciation"
    AUDIO_QUALITY = "audio_quality"
    SIMILARITY = "similarity"


class GenerationInput(FrozenModel):
    job_type: Literal[JobType.VOCAL_GENERATION]
    lyrics_reference: str
    melody_reference: str
    timing_reference: str | None = None
    voice_reference: str | None = None
    processing_chain_id: str | None = None


class VoiceConversionInput(FrozenModel):
    job_type: Literal[JobType.VOICE_CONVERSION]
    source_asset_version_id: str
    parent_asset_version_id: str | None = None
    voice_reference_artifact_id: str
    source_entity_type: Literal["recording_take", "ai_generated_vocal"]
    reference_entity_type: Literal["voice_enrollment_sample"]
    training_dataset_id: None = None
    processing_chain_id: str | None = None


class CorrectionInput(FrozenModel):
    job_type: Literal[JobType.VOCAL_CORRECTION]
    source_asset_version_id: str
    parent_asset_version_id: str | None = None
    correction_types: tuple[CorrectionType, ...] = Field(min_length=1)
    processing_chain_id: str | None = None


class AnalysisInput(FrozenModel):
    job_type: Literal[JobType.VOCAL_ANALYSIS]
    source_asset_version_id: str
    parent_asset_version_id: str | None = None
    analysis_types: tuple[AnalysisType, ...] = Field(min_length=1)
    processing_chain_id: str | None = None


VocalJobInput = Annotated[
    GenerationInput | VoiceConversionInput | CorrectionInput | AnalysisInput,
    Field(discriminator="job_type"),
]


class CreateVocalJobRequest(FrozenModel):
    provider_id: str
    capability: JobType
    api_contract_version: str
    idempotency_key: str = Field(min_length=1, max_length=200)
    project_id: str
    input_asset_version_ids: tuple[str, ...] = ()
    input_artifact_ids: tuple[str, ...] = ()
    model_manifest_id: str
    settings_snapshot: dict[str, Any] = Field(default_factory=dict)
    requested_by: str
    composition_snapshot_id: str | None = None
    job_input: VocalJobInput

    @field_validator("settings_snapshot", mode="before")
    @classmethod
    def copy_settings_snapshot(cls, value: Any) -> Any:
        """Detach nested caller-owned containers at the request boundary."""

        return deepcopy(value)

    @model_validator(mode="after")
    def capability_matches_job_input(self) -> "CreateVocalJobRequest":
        if self.capability != self.job_input.job_type:
            raise ValueError("capability과 job_input.job_type이 일치해야 합니다.")
        self._reject_sensitive_or_path_values(self.model_dump(mode="python"))
        return self

    @classmethod
    def _reject_sensitive_or_path_values(cls, value: Any, key: str = "") -> None:
        forbidden_keys = {
            "api_key",
            "credential",
            "dataset_path",
            "model_path",
            "password",
            "path",
            "secret",
            "token",
        }
        if key.lower() in forbidden_keys:
            raise ValueError("settings_snapshot에 민감한 설정을 포함할 수 없습니다.")
        if isinstance(value, dict):
            for nested_key, nested_value in value.items():
                cls._reject_sensitive_or_path_values(nested_value, str(nested_key))
        elif isinstance(value, (list, tuple)):
            for item in value:
                cls._reject_sensitive_or_path_values(item, key)
        elif isinstance(value, str) and cls._looks_like_path(value):
            raise ValueError("Provider 요청에 파일 경로를 포함할 수 없습니다.")

    @staticmethod
    def _looks_like_path(value: str) -> bool:
        return bool(
            re.match(r"^[A-Za-z]:[\\/]", value)
            or value.startswith(("/", "\\", "~/", "~\\"))
            or re.search(r"(^|[\\/])\.\.([\\/]|$)", value)
            or re.search(r"(^|:)file://", value, flags=re.IGNORECASE)
        )


class BaseVocalJob(FrozenModel):
    job_id: str
    job_type: JobType
    status: JobStatus
    provider_id: str
    api_contract_version: str
    progress_percent: int = Field(ge=0, le=100)
    input_asset_version_ids: tuple[str, ...]
    input_artifact_ids: tuple[str, ...]
    output_asset_version_ids: tuple[str, ...] = ()
    output_artifact_ids: tuple[str, ...] = ()
    composition_snapshot_id: str | None = None
    settings_snapshot: dict[str, Any]
    model_manifest_id: str
    retry_of_job_id: str | None = None
    error: ErrorDetail | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class VocalGenerationJob(BaseVocalJob):
    job_type: Literal[JobType.VOCAL_GENERATION]


class VoiceConversionJob(BaseVocalJob):
    job_type: Literal[JobType.VOICE_CONVERSION]


class VocalCorrectionJob(BaseVocalJob):
    job_type: Literal[JobType.VOCAL_CORRECTION]


class VocalAnalysisJob(BaseVocalJob):
    job_type: Literal[JobType.VOCAL_ANALYSIS]


AnyVocalJob = (
    VocalGenerationJob | VoiceConversionJob | VocalCorrectionJob | VocalAnalysisJob
)


TERMINAL_STATUSES = frozenset(
    {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}
)
ALLOWED_TRANSITIONS = {
    JobStatus.QUEUED: frozenset({JobStatus.RUNNING, JobStatus.CANCELLED}),
    JobStatus.RUNNING: frozenset(
        {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}
    ),
}
