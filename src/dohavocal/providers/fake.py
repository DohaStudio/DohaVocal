"""Deterministic metadata-only Provider for contract and lifecycle validation."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from dohavocal.artifacts.memory import InMemoryArtifactStore
from dohavocal.config import RuntimeSettings
from dohavocal.domain.artifacts import ArtifactLineage, VocalArtifact
from dohavocal.domain.errors import (
    ConflictError,
    ContractVersionError,
    ErrorDetail,
    InvalidStateTransitionError,
    NotFoundError,
    UnsupportedCapabilityError,
)
from dohavocal.domain.jobs import (
    ALLOWED_TRANSITIONS,
    AnalysisInput,
    AnyVocalJob,
    CorrectionInput,
    CreateVocalJobRequest,
    JobStatus,
    JobType,
    VocalAnalysisJob,
    VocalCorrectionJob,
    VocalGenerationJob,
    VoiceConversionInput,
    VoiceConversionJob,
)
from dohavocal.domain.manifests import ModelManifest
from dohavocal.providers.state import InMemoryJobStore

JOB_CLASSES = {
    JobType.VOCAL_GENERATION: VocalGenerationJob,
    JobType.VOICE_CONVERSION: VoiceConversionJob,
    JobType.VOCAL_CORRECTION: VocalCorrectionJob,
    JobType.VOCAL_ANALYSIS: VocalAnalysisJob,
}


class FakeVocalProvider:
    """No audio I/O, model download, subprocess, network call, or GPU execution."""

    def __init__(
        self,
        settings: RuntimeSettings | None = None,
        jobs: InMemoryJobStore | None = None,
        artifacts: InMemoryArtifactStore | None = None,
    ) -> None:
        self.settings = settings or RuntimeSettings()
        self.jobs = jobs or InMemoryJobStore()
        self.artifacts = artifacts or InMemoryArtifactStore()
        manifest_payload = f"{self.settings.model_manifest_id}:metadata-only".encode()
        self._manifest = ModelManifest(
            model_manifest_id=self.settings.model_manifest_id,
            provider_id=self.settings.provider_id,
            model_id="fake-vocal-model",
            model_version="0.1.0",
            checkpoint_version="not-applicable",
            model_type="deterministic_metadata_fake",
            capabilities=self.get_capabilities(),
            input_formats=("application/json",),
            output_formats=("application/json",),
            api_contract_version=self.settings.api_contract_version,
            license_status="REVIEW_REQUIRED",
            commercial_usage_status="REVIEW_REQUIRED",
            recommended_vram=None,
            runtime_environment={"execution": "metadata-only", "gpu": "not-used"},
            artifact_checksum=hashlib.sha256(manifest_payload).hexdigest(),
            created_at=datetime.now(UTC),
        )

    def get_capabilities(self) -> tuple[JobType, ...]:
        return tuple(JobType)

    def create_job(self, request: CreateVocalJobRequest) -> AnyVocalJob:
        self._validate_request(request)
        fingerprint = self._fingerprint(request)
        replay = self.jobs.resolve_idempotency(request, fingerprint)
        if replay is not None:
            return replay

        now = datetime.now(UTC)
        job_class = JOB_CLASSES[request.capability]
        job = job_class(
            job_id=str(uuid4()),
            job_type=request.capability,
            status=JobStatus.QUEUED,
            provider_id=request.provider_id,
            api_contract_version=request.api_contract_version,
            progress_percent=0,
            input_asset_version_ids=request.input_asset_version_ids,
            input_artifact_ids=request.input_artifact_ids,
            composition_snapshot_id=request.composition_snapshot_id,
            settings_snapshot=json.loads(
                json.dumps(request.settings_snapshot, sort_keys=True)
            ),
            model_manifest_id=request.model_manifest_id,
            created_at=now,
        )
        race_replay = self.jobs.add(job, request, fingerprint)
        if race_replay is not None:
            return race_replay

        outcome = request.settings_snapshot.get("fake_outcome", "succeeded")
        if outcome == "queued":
            return self.jobs.get(job.job_id)
        running = self.transition(job.job_id, JobStatus.RUNNING, progress_percent=50)
        if outcome == "running":
            return running
        if outcome == "failed":
            return self.transition(
                job.job_id,
                JobStatus.FAILED,
                error=ErrorDetail(
                    error_code="FAKE_PROCESSING_FAILED",
                    message="Fake Provider가 요청된 실패 결과를 생성했습니다.",
                    retryable=True,
                    stage="fake_processing",
                    details_id="fake-failure",
                ),
            )
        artifact = self._build_artifact(job.job_id, request)
        self.artifacts.add(artifact)
        return self.transition(
            job.job_id,
            JobStatus.SUCCEEDED,
            progress_percent=100,
            output_asset_version_ids=(artifact.output_asset_version_id,),
            output_artifact_ids=(artifact.artifact_id,),
        )

    def get_job_status(self, job_id: str) -> AnyVocalJob:
        return self.jobs.get(job_id)

    def cancel_job(self, job_id: str) -> AnyVocalJob:
        return self.transition(job_id, JobStatus.CANCELLED)

    def retry_job(self, job_id: str) -> AnyVocalJob:
        original = self.jobs.get(job_id)
        if original.status not in {JobStatus.FAILED, JobStatus.CANCELLED}:
            raise InvalidStateTransitionError(
                "JOB_RETRY_NOT_ALLOWED",
                "실패하거나 취소된 Job만 재시도할 수 있습니다.",
                stage="retry",
            )
        request = self.jobs.get_request(job_id)
        retry_request = request.model_copy(
            update={"idempotency_key": f"retry:{job_id}:{uuid4()}"}
        )
        retry_job = self.create_job(retry_request)
        updated = retry_job.model_copy(update={"retry_of_job_id": original.job_id})
        self.jobs.replace(updated)
        return updated

    def get_result(self, job_id: str) -> VocalArtifact:
        job = self.jobs.get(job_id)
        if job.status != JobStatus.SUCCEEDED or not job.output_artifact_ids:
            raise ConflictError(
                "JOB_RESULT_NOT_AVAILABLE",
                "성공한 Job에만 결과가 있습니다.",
                retryable=job.status in {JobStatus.QUEUED, JobStatus.RUNNING},
                stage="result_lookup",
            )
        return self.artifacts.get(job.output_artifact_ids[0])

    def get_model_manifest(self, model_manifest_id: str) -> ModelManifest:
        if model_manifest_id != self._manifest.model_manifest_id:
            raise NotFoundError(
                "MODEL_MANIFEST_NOT_FOUND",
                "Model Manifest를 찾을 수 없습니다.",
                stage="manifest_lookup",
            )
        return self._manifest.model_copy(deep=True)

    def health(self) -> bool:
        return True

    def readiness(self) -> bool:
        return True

    def transition(
        self,
        job_id: str,
        target: JobStatus,
        *,
        progress_percent: int | None = None,
        error: ErrorDetail | None = None,
        output_asset_version_ids: tuple[str, ...] | None = None,
        output_artifact_ids: tuple[str, ...] | None = None,
    ) -> AnyVocalJob:
        job = self.jobs.get(job_id)
        if target not in ALLOWED_TRANSITIONS.get(job.status, frozenset()):
            raise InvalidStateTransitionError(
                "STATE_TRANSITION_INVALID",
                f"{job.status.value}에서 {target.value}(으)로 전이할 수 없습니다.",
                stage="state_transition",
            )
        if target == JobStatus.FAILED and error is None:
            raise InvalidStateTransitionError(
                "STATE_TRANSITION_INVALID",
                "failed 상태에는 구조화된 error가 필요합니다.",
                stage="state_transition",
            )
        if target == JobStatus.SUCCEEDED and (
            not output_asset_version_ids or not output_artifact_ids
        ):
            raise InvalidStateTransitionError(
                "STATE_TRANSITION_INVALID",
                "succeeded 상태에는 검증된 output ID가 필요합니다.",
                stage="state_transition",
            )
        now = datetime.now(UTC)
        updates: dict[str, Any] = {"status": target}
        if target == JobStatus.RUNNING:
            updates["started_at"] = now
        if target in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}:
            updates["completed_at"] = now
        if progress_percent is not None:
            updates["progress_percent"] = progress_percent
        if error is not None:
            updates["error"] = error
        if output_asset_version_ids is not None:
            updates["output_asset_version_ids"] = output_asset_version_ids
        if output_artifact_ids is not None:
            updates["output_artifact_ids"] = output_artifact_ids
        updated = job.model_copy(update=updates)
        return self.jobs.replace_if_status(updated, job.status)

    def _validate_request(self, request: CreateVocalJobRequest) -> None:
        if request.provider_id != self.settings.provider_id:
            raise UnsupportedCapabilityError(
                "PROVIDER_NOT_SUPPORTED",
                "요청한 Provider를 지원하지 않습니다.",
            )
        if request.capability not in self.get_capabilities():
            raise UnsupportedCapabilityError(
                "CAPABILITY_NOT_SUPPORTED",
                "요청한 capability를 지원하지 않습니다.",
            )
        if request.api_contract_version != self.settings.api_contract_version:
            raise ContractVersionError(
                "CONTRACT_VERSION_UNSUPPORTED",
                "요청한 API contract version을 지원하지 않습니다.",
            )
        if request.model_manifest_id != self._manifest.model_manifest_id:
            raise NotFoundError(
                "MODEL_MANIFEST_NOT_FOUND",
                "Model Manifest를 찾을 수 없습니다.",
                stage="job_creation",
            )

    @staticmethod
    def _fingerprint(request: CreateVocalJobRequest) -> str:
        payload = request.model_dump(mode="json", exclude={"idempotency_key"})
        canonical = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _build_artifact(
        self, job_id: str, request: CreateVocalJobRequest
    ) -> VocalArtifact:
        artifact_id = str(uuid4())
        output_asset_version_id = str(uuid4())
        source_asset_version_id, parent_asset_version_id = self._lineage_versions(
            request
        )
        processing_chain_id = request.job_input.processing_chain_id or str(uuid4())
        created_at = datetime.now(UTC)
        processing_types = self._processing_types(request)
        content_descriptor = {
            "schema": "dohavocal.fake-artifact-metadata.v1",
            "job_id": job_id,
            "capability": request.capability.value,
            "source_asset_version_id": source_asset_version_id,
            "parent_asset_version_id": parent_asset_version_id,
            "processing_chain_id": processing_chain_id,
            "model_manifest_id": request.model_manifest_id,
            "settings_snapshot": request.settings_snapshot,
            "processing_types": processing_types,
        }
        checksum = hashlib.sha256(
            json.dumps(
                content_descriptor,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        analysis = None
        artifact_kind = "audio"
        media_type = "audio/x-dohavocal-fake"
        if isinstance(request.job_input, AnalysisInput):
            artifact_kind = "analysis"
            media_type = "application/json"
            analysis = {
                analysis_type.value: {"status": "fake", "value": None}
                for analysis_type in request.job_input.analysis_types
            }
        return VocalArtifact(
            artifact_id=artifact_id,
            artifact_kind=artifact_kind,
            media_type=media_type,
            size_bytes=0,
            artifact_checksum=checksum,
            producer_id=self.settings.provider_id,
            run_id=job_id,
            output_asset_version_id=output_asset_version_id,
            lineage=ArtifactLineage(
                source_asset_version_id=source_asset_version_id,
                parent_asset_version_id=parent_asset_version_id,
                processing_chain_id=processing_chain_id,
                provider_id=request.provider_id,
                model_manifest_id=request.model_manifest_id,
                settings_snapshot=json.loads(
                    json.dumps(request.settings_snapshot, sort_keys=True)
                ),
                processing_types=processing_types,
                created_at=created_at,
                checksum=checksum,
                source_artifact_id=(
                    request.input_artifact_ids[0]
                    if request.input_artifact_ids
                    else None
                ),
                parent_artifact_id=(
                    request.input_artifact_ids[0]
                    if request.input_artifact_ids
                    else None
                ),
                job_id=job_id,
            ),
            analysis_result=analysis,
        )

    @staticmethod
    def _lineage_versions(request: CreateVocalJobRequest) -> tuple[str, str]:
        if isinstance(
            request.job_input, (VoiceConversionInput, CorrectionInput, AnalysisInput)
        ):
            source = request.job_input.source_asset_version_id
            return source, request.job_input.parent_asset_version_id or source
        if request.input_asset_version_ids:
            source = request.input_asset_version_ids[0]
            return source, source
        source = f"generated-source:{request.project_id}"
        return source, source

    @staticmethod
    def _processing_types(request: CreateVocalJobRequest) -> tuple[str, ...]:
        if isinstance(request.job_input, CorrectionInput):
            return tuple(item.value for item in request.job_input.correction_types)
        if isinstance(request.job_input, AnalysisInput):
            return tuple(item.value for item in request.job_input.analysis_types)
        return (request.capability.value,)
