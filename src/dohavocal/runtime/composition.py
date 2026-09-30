"""Trusted Runtime configuration composes adapters outside Provider business logic."""

from dohavocal.config import RuntimeSettings
from dohavocal.persistence.sqlite import SQLiteRuntimeStore, unavailable
from dohavocal.providers import FakeVocalProvider


def build_provider(settings: RuntimeSettings) -> FakeVocalProvider:
    if settings.runtime_mode == "memory":
        if settings.database_path is not None or settings.initialize_database:
            raise unavailable("DURABLE_CONFIGURATION_INVALID")
        return FakeVocalProvider(settings)
    if settings.runtime_mode != "sqlite" or settings.database_path is None:
        raise unavailable("DURABLE_CONFIGURATION_INVALID")
    store = SQLiteRuntimeStore(
        settings.database_path,
        initialize=settings.initialize_database,
        busy_timeout_ms=settings.busy_timeout_ms,
    )
    return FakeVocalProvider(
        settings, store.jobs, store.artifacts, store.payloads, store
    )
