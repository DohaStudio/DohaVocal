"""Default process-local unit of work; individual stores retain their locks."""

from contextlib import nullcontext


class MemoryUnitOfWork:
    def transaction(self):
        return nullcontext()

    def checkpoint(self, name: str) -> None:
        pass

    def readiness(self) -> bool:
        return True

    def close(self) -> None:
        pass
