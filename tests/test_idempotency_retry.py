from concurrent.futures import ThreadPoolExecutor

import pytest

from dohavocal.domain.errors import ConflictError
from dohavocal.domain.jobs import JobType


def test_same_key_and_fingerprint_replays_without_duplicates(provider, request_factory):
    request = request_factory(idempotency_key="stable-key")

    first = provider.create_job(request)
    replay = provider.create_job(request)

    assert replay.job_id == first.job_id
    assert provider.jobs.count() == 1
    assert provider.artifacts.count() == 1


def test_same_scope_key_and_different_fingerprint_conflicts(provider, request_factory):
    first = request_factory(idempotency_key="conflict-key", settings={"value": 1})
    second = first.model_copy(update={"settings_snapshot": {"value": 2}})
    provider.create_job(first)

    with pytest.raises(ConflictError) as caught:
        provider.create_job(second)

    assert caught.value.detail.error_code == "IDEMPOTENCY_CONFLICT"
    assert provider.jobs.count() == 1
    assert provider.artifacts.count() == 1


def test_canonical_fingerprint_normalizes_mapping_key_order(provider, request_factory):
    first = request_factory(
        idempotency_key="canonical-key", settings={"alpha": 1, "beta": 2}
    )
    second = first.model_copy(update={"settings_snapshot": {"beta": 2, "alpha": 1}})

    assert provider.create_job(first).job_id == provider.create_job(second).job_id


def test_same_key_in_different_project_scope_does_not_collide(
    provider, request_factory
):
    first = request_factory(idempotency_key="shared-key")
    second = first.model_copy(update={"project_id": "project-2"})

    assert provider.create_job(first).job_id != provider.create_job(second).job_id


def test_same_key_in_different_capability_scope_does_not_collide(
    provider, request_factory
):
    first = request_factory(JobType.VOCAL_GENERATION, idempotency_key="shared-key")
    second = request_factory(JobType.VOCAL_ANALYSIS, idempotency_key="shared-key")

    assert provider.create_job(first).job_id != provider.create_job(second).job_id


def test_same_key_in_different_requester_scope_does_not_collide(
    provider, request_factory
):
    first = request_factory(idempotency_key="shared-key")
    second = first.model_copy(update={"requested_by": "actor-2"})

    assert provider.create_job(first).job_id != provider.create_job(second).job_id


def test_concurrent_same_request_creates_one_job_and_artifact(
    provider, request_factory
):
    request = request_factory(idempotency_key="concurrent-key")

    with ThreadPoolExecutor(max_workers=8) as executor:
        jobs = list(
            executor.map(lambda _index: provider.create_job(request), range(16))
        )

    assert len({job.job_id for job in jobs}) == 1
    assert provider.jobs.count() == 1
    assert provider.artifacts.count() == 1


def test_retry_creates_new_job_and_preserves_original(provider, request_factory):
    original = provider.create_job(request_factory(settings={"fake_outcome": "failed"}))
    original_snapshot = original.model_dump(mode="json")

    retried = provider.retry_job(original.job_id)

    assert retried.job_id != original.job_id
    assert retried.retry_of_job_id == original.job_id
    assert provider.get_job_status(original.job_id).model_dump(mode="json") == (
        original_snapshot
    )
