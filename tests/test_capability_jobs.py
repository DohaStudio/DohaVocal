from dohavocal.domain.jobs import JobStatus, JobType


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
