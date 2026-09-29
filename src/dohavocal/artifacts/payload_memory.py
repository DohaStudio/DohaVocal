"""Process-local Fake bytes, separate from the public Result descriptor store."""

import hashlib
from datetime import UTC, datetime
from threading import RLock

from dohavocal.domain.errors import ConflictError, NotFoundError, VocalRuntimeError
from dohavocal.domain.payloads import (
    PayloadArtifact,
    PayloadContent,
    SourceScope,
    source_scope,
)


class PayloadExpiredError(VocalRuntimeError):
    status_code = 410


def replay_conflict() -> ConflictError:
    return ConflictError(
        "PROVIDER_RESULT_REPLAY_CONFLICT",
        "저장된 Result binding과 일치하지 않습니다.",
        stage="payload_validation",
    )


class InMemoryPayloadStore:
    def __init__(self) -> None:
        self._content: dict[SourceScope, bytes] = {}
        self._results: dict[str, str] = {}
        self._lock = RLock()

    def add(self, result: PayloadArtifact, content: bytes) -> None:
        entry = result.payloads[0]
        if (
            len(content) != entry.expected_size_bytes
            or hashlib.sha256(content).hexdigest() != entry.payload_checksum
        ):
            raise replay_conflict()
        with self._lock:
            if result.run_id in self._results or source_scope(result) in self._content:
                raise replay_conflict()
            self._results[result.run_id] = result.model_dump_json()
            self._content[source_scope(result)] = bytes(content)

    def verify_result(self, result: PayloadArtifact) -> None:
        with self._lock:
            if self._results.get(result.run_id) != result.model_dump_json():
                raise replay_conflict()

    def acquire(self, result: PayloadArtifact) -> PayloadContent:
        self.verify_result(result)
        entry = result.payloads[0]
        if entry.available_until is not None and entry.available_until <= datetime.now(
            UTC
        ):
            raise PayloadExpiredError(
                "PROVIDER_PAYLOAD_EXPIRED",
                "Payload 제공 기간이 종료되었습니다.",
                stage="payload_acquisition",
            )
        with self._lock:
            content = self._content.get(source_scope(result))
        if content is None:
            raise NotFoundError(
                "PROVIDER_PAYLOAD_UNAVAILABLE",
                "Payload를 제공할 수 없습니다.",
                stage="payload_acquisition",
            )
        if (
            len(content) != entry.expected_size_bytes
            or hashlib.sha256(content).hexdigest() != entry.payload_checksum
        ):
            raise replay_conflict()
        return PayloadContent(content, entry.expected_media_type)

    def contains_source(self, source_id: str) -> bool:
        with self._lock:
            return any(scope[-1] == source_id for scope in self._content)

    def count(self) -> int:
        with self._lock:
            return len(self._content)
