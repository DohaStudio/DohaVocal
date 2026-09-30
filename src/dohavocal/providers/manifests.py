"""Canonical source-controlled Fake descriptors, independent of Runtime startup."""

import hashlib
from datetime import UTC, datetime

from dohavocal.config.settings import DOHAVOCAL_PROVIDER_ID
from dohavocal.domain.jobs import JobType
from dohavocal.domain.manifests import ModelManifest


def fake_manifests() -> tuple[ModelManifest, ModelManifest]:
    """Return detached definitions; publication instants come from merged history.

    0.1.0: e785ed0e0ece8acd09fad6bf29addafa8fd22002 (PR #4).
    0.2.0: e28320ef26a2dc49eaefdfa62bceea0c8c69e6ed (PR #7).
    These are descriptor publication times, never process or DB registration times.
    """
    metadata = ModelManifest(
        model_manifest_id="dohavocal.fake-model@0.1.0",
        provider_id=DOHAVOCAL_PROVIDER_ID,
        model_id="fake-vocal-model",
        model_version="0.1.0",
        checkpoint_version="not-applicable",
        model_type="deterministic_metadata_fake",
        capabilities=tuple(JobType),
        input_formats=("application/json",),
        output_formats=("application/json",),
        api_contract_version="0.1.0",
        license_status="REVIEW_REQUIRED",
        commercial_usage_status="REVIEW_REQUIRED",
        recommended_vram=None,
        runtime_environment={"execution": "metadata-only", "gpu": "not-used"},
        artifact_checksum=hashlib.sha256(
            b"dohavocal.fake-model@0.1.0:metadata-only"
        ).hexdigest(),
        created_at=datetime(2026, 8, 19, 4, 26, 36, tzinfo=UTC),
    )
    payload = ModelManifest.model_validate(
        {
            **metadata.model_dump(),
            "model_manifest_id": "dohavocal.fake-model@0.2.0",
            "model_version": "0.2.0",
            "api_contract_version": "0.2.0",
            "output_formats": ("audio/wav", "application/json"),
            "runtime_environment": {
                "execution": "payload-backed-fake",
                "gpu": "not-used",
                "persistence": "runtime-configured",
                "authentication": "not-implemented-development-only",
            },
            "artifact_checksum": hashlib.sha256(
                b"dohavocal.fake-model@0.2.0:payload-backed-fake"
            ).hexdigest(),
            "created_at": datetime(2026, 9, 29, 13, 32, 50, tzinfo=UTC),
        }
    )
    return metadata, payload
