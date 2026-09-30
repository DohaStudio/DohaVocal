"""Environment-independent defaults for the foundation runtime."""

from dataclasses import dataclass, field
from pathlib import Path

DOHAVOCAL_PROVIDER_ID = "dohavocal"


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    provider_id: str = field(init=False, default=DOHAVOCAL_PROVIDER_ID)
    api_contract_version: str = "0.1.0"
    model_manifest_id: str = "dohavocal.fake-model@0.1.0"

    runtime_mode: str = "memory"
    database_path: Path | None = field(default=None, repr=False)
    initialize_database: bool = False
    busy_timeout_ms: int = 5000
