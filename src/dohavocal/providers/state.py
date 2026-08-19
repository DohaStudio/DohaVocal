"""In-memory Job state and idempotency repositories."""

from copy import deepcopy
from dataclasses import dataclass
from threading import RLock

from dohavocal.domain.errors import (
    ConflictError,
    InvalidStateTransitionError,
    NotFoundError,
)
from dohavocal.domain.jobs import AnyVocalJob, CreateVocalJobRequest, JobStatus


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    fingerprint: str
    job_id: str


class InMemoryJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, AnyVocalJob] = {}
        self._requests: dict[str, CreateVocalJobRequest] = {}
        self._idempotency: dict[tuple[str, str, str, str, str], IdempotencyRecord] = {}
        self._lock = RLock()

    @staticmethod
    def scope(request: CreateVocalJobRequest) -> tuple[str, str, str, str, str]:
        return (
            request.provider_id,
            request.capability.value,
            request.project_id,
            request.requested_by,
            request.idempotency_key,
        )

    def resolve_idempotency(
        self, request: CreateVocalJobRequest, fingerprint: str
    ) -> AnyVocalJob | None:
        with self._lock:
            record = self._idempotency.get(self.scope(request))
            if record is None:
                return None
            if record.fingerprint != fingerprint:
                raise ConflictError(
                    "IDEMPOTENCY_CONFLICT",
                    "같은 idempotency key가 다른 요청에 사용되었습니다.",
                    stage="job_creation",
                )
            return deepcopy(self._jobs[record.job_id])

    def add(
        self, job: AnyVocalJob, request: CreateVocalJobRequest, fingerprint: str
    ) -> AnyVocalJob | None:
        with self._lock:
            existing = self._idempotency.get(self.scope(request))
            if existing is not None:
                if existing.fingerprint != fingerprint:
                    raise ConflictError(
                        "IDEMPOTENCY_CONFLICT",
                        "같은 idempotency key가 다른 요청에 사용되었습니다.",
                        stage="job_creation",
                    )
                return deepcopy(self._jobs[existing.job_id])
            if job.job_id in self._jobs:
                raise ValueError("Job ID는 덮어쓸 수 없습니다.")
            self._jobs[job.job_id] = deepcopy(job)
            self._requests[job.job_id] = deepcopy(request)
            self._idempotency[self.scope(request)] = IdempotencyRecord(
                fingerprint=fingerprint, job_id=job.job_id
            )
            return None

    def get(self, job_id: str) -> AnyVocalJob:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise NotFoundError(
                    "JOB_NOT_FOUND",
                    "Job을 찾을 수 없습니다.",
                    stage="job_lookup",
                )
            return deepcopy(job)

    def get_request(self, job_id: str) -> CreateVocalJobRequest:
        self.get(job_id)
        with self._lock:
            return deepcopy(self._requests[job_id])

    def replace(self, job: AnyVocalJob) -> None:
        with self._lock:
            if job.job_id not in self._jobs:
                raise NotFoundError(
                    "JOB_NOT_FOUND", "Job을 찾을 수 없습니다.", stage="job_lookup"
                )
            self._jobs[job.job_id] = deepcopy(job)

    def replace_if_status(
        self, job: AnyVocalJob, expected_status: JobStatus
    ) -> AnyVocalJob:
        """Atomically replace a Job only when its current state is unchanged."""

        with self._lock:
            current = self._jobs.get(job.job_id)
            if current is None:
                raise NotFoundError(
                    "JOB_NOT_FOUND", "Job을 찾을 수 없습니다.", stage="job_lookup"
                )
            if current.status != expected_status:
                raise InvalidStateTransitionError(
                    "STATE_TRANSITION_INVALID",
                    "동시에 변경된 Job 상태에서는 요청한 전이를 적용할 수 없습니다.",
                    stage="state_transition",
                )
            self._jobs[job.job_id] = deepcopy(job)
            return deepcopy(job)

    def count(self) -> int:
        with self._lock:
            return len(self._jobs)
