import pytest

from dohavocal.domain.errors import InvalidStateTransitionError
from dohavocal.domain.jobs import JobStatus


def test_queued_to_running_to_succeeded(provider, request_factory):
    job = provider.create_job(request_factory(settings={"fake_outcome": "queued"}))
    assert job.status == JobStatus.QUEUED

    running = provider.transition(job.job_id, JobStatus.RUNNING, progress_percent=30)
    succeeded = provider.transition(
        job.job_id, JobStatus.SUCCEEDED, progress_percent=100
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
    failed = provider.transition(running_failure.job_id, JobStatus.FAILED)
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
