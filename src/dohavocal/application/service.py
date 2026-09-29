"""Thin application boundary shared by the HTTP API and tests."""

from dohavocal.application.ports import VocalProvider
from dohavocal.domain.jobs import AnyVocalJob, CreateVocalJobRequest, JobType
from dohavocal.domain.manifests import ModelManifest
from dohavocal.domain.payloads import AnyVocalArtifact, PayloadContent


class VocalRuntimeService:
    def __init__(self, provider: VocalProvider) -> None:
        self._provider = provider

    def get_capabilities(self) -> tuple[JobType, ...]:
        return self._provider.get_capabilities()

    def create_job(self, request: CreateVocalJobRequest) -> AnyVocalJob:
        return self._provider.create_job(request)

    def get_job(self, job_id: str) -> AnyVocalJob:
        return self._provider.get_job_status(job_id)

    def cancel_job(self, job_id: str) -> AnyVocalJob:
        return self._provider.cancel_job(job_id)

    def retry_job(self, job_id: str) -> AnyVocalJob:
        return self._provider.retry_job(job_id)

    def get_result(self, job_id: str) -> AnyVocalArtifact:
        return self._provider.get_result(job_id)

    def get_model_manifest(self, model_manifest_id: str) -> ModelManifest:
        return self._provider.get_model_manifest(model_manifest_id)

    def get_payload_content(
        self, job_id: str, provider_artifact_id: str, source_id: str
    ) -> PayloadContent:
        return self._provider.get_payload_content(
            job_id, provider_artifact_id, source_id
        )

    def supported_contract_versions(self) -> tuple[str, ...]:
        return self._provider.supported_contract_versions()

    def health(self) -> bool:
        return self._provider.health()

    def readiness(self) -> bool:
        return self._provider.readiness()
