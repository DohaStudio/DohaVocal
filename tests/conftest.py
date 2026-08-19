from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from dohavocal.api.app import create_app
from dohavocal.application import VocalRuntimeService
from dohavocal.domain.jobs import CreateVocalJobRequest, JobType
from dohavocal.providers import FakeVocalProvider


@pytest.fixture
def provider() -> FakeVocalProvider:
    return FakeVocalProvider()


@pytest.fixture
def client(provider: FakeVocalProvider) -> TestClient:
    return TestClient(create_app(VocalRuntimeService(provider)))


@pytest.fixture
def request_factory() -> Callable[..., CreateVocalJobRequest]:
    sequence = 0

    def make_request(
        job_type: JobType = JobType.VOCAL_GENERATION,
        *,
        settings: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> CreateVocalJobRequest:
        nonlocal sequence
        sequence += 1
        inputs: dict[JobType, dict[str, Any]] = {
            JobType.VOCAL_GENERATION: {
                "job_type": "vocal_generation",
                "lyrics_reference": "artifact:lyrics-1",
                "melody_reference": "asset-version:melody-1",
                "timing_reference": "snapshot:timing-1",
                "voice_reference": "model:voice-1",
            },
            JobType.VOICE_CONVERSION: {
                "job_type": "voice_conversion",
                "source_asset_version_id": "asset-version:recording-1",
                "voice_reference_artifact_id": "artifact:enrollment-1",
                "source_entity_type": "recording_take",
                "reference_entity_type": "voice_enrollment_sample",
                "training_dataset_id": None,
            },
            JobType.VOCAL_CORRECTION: {
                "job_type": "vocal_correction",
                "source_asset_version_id": "asset-version:raw-vocal-1",
                "correction_types": ["pitch_correction", "de_esser"],
            },
            JobType.VOCAL_ANALYSIS: {
                "job_type": "vocal_analysis",
                "source_asset_version_id": "asset-version:analysis-source-1",
                "analysis_types": ["pitch", "timing", "similarity"],
            },
        }
        return CreateVocalJobRequest.model_validate(
            {
                "provider_id": "dohavocal.fake",
                "capability": job_type.value,
                "api_contract_version": "0.1.0",
                "idempotency_key": idempotency_key or f"request-{sequence}",
                "project_id": "project-1",
                "input_asset_version_ids": ["asset-version:input-1"],
                "input_artifact_ids": ["artifact:input-1"],
                "model_manifest_id": "dohavocal.fake-model@0.1.0",
                "settings_snapshot": settings or {},
                "requested_by": "actor-1",
                "composition_snapshot_id": "snapshot-1",
                "job_input": inputs[job_type],
            }
        )

    return make_request


@pytest.fixture
def generation_payload() -> dict[str, Any]:
    return {
        "provider_id": "dohavocal.fake",
        "capability": "vocal_generation",
        "api_contract_version": "0.1.0",
        "idempotency_key": "api-generation-1",
        "project_id": "project-1",
        "input_asset_version_ids": ["asset-version:melody-1"],
        "input_artifact_ids": ["artifact:lyrics-1"],
        "model_manifest_id": "dohavocal.fake-model@0.1.0",
        "settings_snapshot": {"temperature": 0},
        "requested_by": "actor-1",
        "composition_snapshot_id": "snapshot-1",
        "job_input": {
            "job_type": "vocal_generation",
            "lyrics_reference": "artifact:lyrics-1",
            "melody_reference": "asset-version:melody-1",
        },
    }
