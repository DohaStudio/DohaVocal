from concurrent.futures import ThreadPoolExecutor

import pytest

from dohavocal.domain.errors import ErrorDetail, InvalidStateTransitionError
from dohavocal.domain.jobs import JobStatus


def test_queued_to_running_to_succeeded(provider, request_factory):
    job = provider.create_job(request_factory(settings={"fake_outcome": "queued"}))
    assert job.status == JobStatus.QUEUED

    running = provider.transition(job.job_id, JobStatus.RUNNING, progress_percent=30)
    succeeded = provider.transition(
        job.job_id,
        JobStatus.SUCCEEDED,
        progress_percent=100,
        output_asset_version_ids=("asset-version:output",),
        output_artifact_ids=("artifact:output",),
    )

    assert running.status == JobStatus.RUNNING
    assert running.started_at is not None
    assert succeeded.status == JobStatus.SUCCEEDED
    assert succeeded.completed_at is not None


def test_queued_can_be_cancelled(provider, request_factory):
    job = provider.create_job(request_factory(settings={"fake_outcome": "queued"}))
    assert provider.cancel_job(job.job_id).status == JobStatus.CANCELLED


def test_running_can_fail_or_cancel(provider, request_factory):
    running_failure = provider.create_job(
        request_factory(settings={"fake_outcome": "running"})
    )
    failed = provider.transition(
        running_failure.job_id,
        JobStatus.FAILED,
        error=ErrorDetail(
            error_code="TEST_FAILURE",
            message="테스트 실패",
            retryable=False,
            stage="test",
            details_id="test-failure",
        ),
    )
    running_cancel = provider.create_job(
        request_factory(settings={"fake_outcome": "running"})
    )
    cancelled = provider.cancel_job(running_cancel.job_id)

    assert failed.status == JobStatus.FAILED
    assert cancelled.status == JobStatus.CANCELLED


@pytest.mark.parametrize(
    "terminal",
    [JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED],
)
def test_terminal_job_rejects_mutation(provider, request_factory, terminal):
    outcome = terminal.value if terminal != JobStatus.CANCELLED else "queued"
    job = provider.create_job(request_factory(settings={"fake_outcome": outcome}))
    if terminal == JobStatus.CANCELLED:
        job = provider.cancel_job(job.job_id)

    with pytest.raises(InvalidStateTransitionError):
        provider.transition(job.job_id, JobStatus.RUNNING)


def test_failed_requires_error_and_succeeded_requires_outputs(
    provider, request_factory
):
    failed_candidate = provider.create_job(
        request_factory(settings={"fake_outcome": "running"})
    )
    success_candidate = provider.create_job(
        request_factory(settings={"fake_outcome": "running"})
    )

    with pytest.raises(InvalidStateTransitionError):
        provider.transition(failed_candidate.job_id, JobStatus.FAILED)
    with pytest.raises(InvalidStateTransitionError):
        provider.transition(success_candidate.job_id, JobStatus.SUCCEEDED)


def test_competing_terminal_transitions_are_atomic(provider, request_factory):
    running = provider.create_job(request_factory(settings={"fake_outcome": "running"}))
    failure = ErrorDetail(
        error_code="TEST_FAILURE",
        message="테스트 실패",
        retryable=False,
        stage="test",
        details_id="test-failure",
    )

    def succeed():
        return provider.transition(
            running.job_id,
            JobStatus.SUCCEEDED,
            progress_percent=100,
            output_asset_version_ids=("asset-version:output",),
            output_artifact_ids=("artifact:output",),
        )

    def fail():
        return provider.transition(running.job_id, JobStatus.FAILED, error=failure)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(succeed), executor.submit(fail)]
    outcomes = []
    for future in futures:
        try:
            outcomes.append(future.result().status)
        except InvalidStateTransitionError:
            outcomes.append("rejected")

    assert outcomes.count("rejected") == 1
    assert provider.get_job_status(running.job_id).status in {
        JobStatus.SUCCEEDED,
        JobStatus.FAILED,
    }
