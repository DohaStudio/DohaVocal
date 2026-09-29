"""In-memory versioned Result descriptors; binary bytes live in a separate store."""

from copy import deepcopy
from threading import RLock

from dohavocal.domain.errors import NotFoundError
from dohavocal.domain.payloads import AnyVocalArtifact


class InMemoryArtifactStore:
    def __init__(self) -> None:
        self._items: dict[str, AnyVocalArtifact] = {}
        self._lock = RLock()

    def add(self, artifact: AnyVocalArtifact) -> None:
        with self._lock:
            if artifact.artifact_id in self._items:
                raise ValueError("Artifact ID는 덮어쓸 수 없습니다.")
            self._items[artifact.artifact_id] = deepcopy(artifact)

    def get(self, artifact_id: str) -> AnyVocalArtifact:
        with self._lock:
            artifact = self._items.get(artifact_id)
            if artifact is None:
                raise NotFoundError(
                    "ARTIFACT_NOT_FOUND",
                    "Artifact를 찾을 수 없습니다.",
                    stage="result_lookup",
                )
            return deepcopy(artifact)

    def count(self) -> int:
        with self._lock:
            return len(self._items)
