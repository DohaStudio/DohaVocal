"""In-memory metadata-only Artifact store used by the foundation runtime."""

from copy import deepcopy
from threading import RLock

from dohavocal.domain.artifacts import VocalArtifact
from dohavocal.domain.errors import NotFoundError


class InMemoryArtifactStore:
    def __init__(self) -> None:
        self._items: dict[str, VocalArtifact] = {}
        self._lock = RLock()

    def add(self, artifact: VocalArtifact) -> None:
        with self._lock:
            if artifact.artifact_id in self._items:
                raise ValueError("Artifact ID는 덮어쓸 수 없습니다.")
            self._items[artifact.artifact_id] = deepcopy(artifact)

    def get(self, artifact_id: str) -> VocalArtifact:
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
