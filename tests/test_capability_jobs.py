import hashlib
import json

from dohavocal.domain.jobs import CorrectionType, JobStatus, JobType


def test_generation_success_links_lineage_and_manifest(provider, request_factory):
    job = provider.create_job(request_factory(JobType.VOCAL_GENERATION))
    result = provider.get_result(job.job_id)

    assert job.status == JobStatus.SUCCEEDED
    assert result.lineage.model_manifest_id == job.model_manifest_id
    assert result.lineage.processing_types == ("vocal_generation",)
    assert result.artifact_checksum == result.lineage.checksum


def test_voice_conversion_preserves_source_parent_and_entity_boundaries(
    provider, request_factory
):
    request = request_factory(JobType.VOICE_CONVERSION)
    job = provider.create_job(request)
    result = provider.get_result(job.job_id)

    assert result.lineage.source_asset_version_id == "asset-version:recording-1"
    assert result.lineage.parent_asset_version_id == "asset-version:recording-1"
    assert request.job_input.source_entity_type == "recording_take"
    assert request.job_input.reference_entity_type == "voice_enrollment_sample"
    assert request.job_input.training_dataset_id is None


def test_correction_is_non_destructive_and_settings_snapshot_isolated(
    provider, request_factory
):
    request = request_factory(
        JobType.VOCAL_CORRECTION, settings={"strength": {"pitch": 0.25}}
    )
    job = provider.create_job(request)
    detached = provider.get_job_status(job.job_id)
    detached.settings_snapshot["strength"]["pitch"] = 1.0
    stored = provider.get_job_status(job.job_id)
    result = provider.get_result(job.job_id)

    assert stored.settings_snapshot["strength"]["pitch"] == 0.25
    assert result.output_asset_version_id != result.lineage.source_asset_version_id
    assert result.lineage.processing_types == ("pitch_correction", "de_esser")


def test_caller_mutation_cannot_change_stored_settings_or_lineage(
    provider, request_factory
):
    caller_settings = {"bands": [{"gain": 1.0}]}
    request = request_factory(JobType.VOCAL_CORRECTION, settings=caller_settings)
    caller_settings["bands"][0]["gain"] = 9.0
    job = provider.create_job(request)
    result = provider.get_result(job.job_id)
    detached = provider.get_result(job.job_id)
    detached.lineage.settings_snapshot["bands"][0]["gain"] = 8.0

    assert (
        provider.get_job_status(job.job_id).settings_snapshot["bands"][0]["gain"] == 1.0
    )
    assert result.lineage.settings_snapshot["bands"][0]["gain"] == 1.0
    assert (
        provider.get_result(job.job_id).lineage.settings_snapshot["bands"][0]["gain"]
        == 1.0
    )


def test_sequential_lineage_preserves_root_parent_and_processing_chain(
    provider, request_factory
):
    pitch_request = request_factory(JobType.VOCAL_CORRECTION)
    pitch_job = provider.create_job(pitch_request)
    pitch_result = provider.get_result(pitch_job.job_id)
    timing_input = pitch_request.job_input.model_copy(
        update={
            "source_asset_version_id": "asset-version:raw-vocal-1",
            "parent_asset_version_id": pitch_result.output_asset_version_id,
            "correction_types": (CorrectionType.TIMING,),
            "processing_chain_id": pitch_result.lineage.processing_chain_id,
        }
    )
    timing_request = request_factory(JobType.VOCAL_CORRECTION).model_copy(
        update={"job_input": timing_input}
    )
    timing_job = provider.create_job(timing_request)
    timing_result = provider.get_result(timing_job.job_id)

    assert timing_result.lineage.source_asset_version_id == "asset-version:raw-vocal-1"
    assert timing_result.lineage.parent_asset_version_id == (
        pitch_result.output_asset_version_id
    )
    assert timing_result.lineage.processing_chain_id == (
        pitch_result.lineage.processing_chain_id
    )
    assert timing_result.lineage.processing_types == ("timing_correction",)


def test_artifact_checksum_is_canonical_metadata_descriptor_checksum(
    provider, request_factory
):
    request = request_factory(JobType.VOCAL_CORRECTION)
    job = provider.create_job(request)
    result = provider.get_result(job.job_id)
    descriptor = {
        "schema": "dohavocal.fake-artifact-metadata.v1",
        "job_id": job.job_id,
        "capability": request.capability.value,
        "source_asset_version_id": result.lineage.source_asset_version_id,
        "parent_asset_version_id": result.lineage.parent_asset_version_id,
        "processing_chain_id": result.lineage.processing_chain_id,
        "model_manifest_id": request.model_manifest_id,
        "settings_snapshot": request.settings_snapshot,
        "processing_types": result.lineage.processing_types,
    }
    expected = hashlib.sha256(
        json.dumps(
            descriptor, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()

    assert result.payload_present is False
    assert result.checksum_scope == "metadata_descriptor"
    assert result.artifact_checksum == expected
    assert result.lineage.checksum == expected


def test_analysis_returns_structured_metadata_without_audio_payload(
    provider, request_factory
):
    job = provider.create_job(request_factory(JobType.VOCAL_ANALYSIS))
    result = provider.get_result(job.job_id)

    assert result.artifact_kind == "analysis"
    assert result.media_type == "application/json"
    assert result.size_bytes == 0
    assert set(result.analysis_result or {}) == {"pitch", "timing", "similarity"}
    assert all(
        value == {"status": "fake", "value": None}
        for value in (result.analysis_result or {}).values()
    )


def test_failure_does_not_create_artifact_or_delete_input(provider, request_factory):
    request = request_factory(settings={"fake_outcome": "failed"})
    job = provider.create_job(request)

    assert job.status == JobStatus.FAILED
    assert job.input_asset_version_ids == request.input_asset_version_ids
    assert provider.artifacts.count() == 0


def test_successful_candidates_are_not_overwritten(provider, request_factory):
    first = provider.create_job(request_factory())
    second = provider.create_job(request_factory())

    assert first.output_artifact_ids != second.output_artifact_ids
    assert first.output_asset_version_ids != second.output_asset_version_ids
    assert provider.artifacts.count() == 2
