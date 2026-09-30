"""Full-document Manifest identity across independent memory/durable processes."""

import json
import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from dohavocal.config import RuntimeSettings
from dohavocal.domain.errors import ContractVersionError
from dohavocal.providers import FakeVocalProvider
from dohavocal.providers.manifests import fake_manifests
from dohavocal.runtime.composition import build_provider


@pytest.mark.parametrize("version", ["0.1.0", "0.2.0"])
def test_complete_manifest_independent_of_runtime_mode(tmp_path, version):
    memory = FakeVocalProvider()
    durable = build_provider(
        RuntimeSettings(
            runtime_mode="sqlite",
            database_path=tmp_path / "runtime.sqlite3",
            initialize_database=True,
        )
    )
    try:
        manifest_id = "dohavocal.fake-model@" + version
        first = memory.get_model_manifest(manifest_id)
        second = durable.get_model_manifest(manifest_id)
        assert first == second
        assert first.model_dump_json() == second.model_dump_json()
        assert first.created_at.utcoffset() == timedelta(0)
        assert first.model_dump(mode="json")["created_at"].endswith("Z")
    finally:
        memory.close()
        durable.close()


@pytest.mark.parametrize("version", ["0.1.0", "0.2.0"])
def test_canonical_copy_and_mutation_boundary(version):
    provider = FakeVocalProvider()
    identifier = "dohavocal.fake-model@" + version
    original = provider.get_model_manifest(identifier)
    changed = provider.get_model_manifest(identifier)
    changed.runtime_environment["gpu"] = "mutated"
    with pytest.raises(ValidationError):
        changed.created_at = original.created_at
    assert provider.get_model_manifest(identifier) == original
    assert FakeVocalProvider().get_model_manifest(identifier) == original
    pair = fake_manifests()
    pair[0].runtime_environment["gpu"] = "mutated-factory-copy"
    assert fake_manifests()[0].runtime_environment["gpu"] == "not-used"


@pytest.mark.parametrize(
    "settings",
    [
        RuntimeSettings(api_contract_version="0.2.0"),
        RuntimeSettings(model_manifest_id="custom-model"),
    ],
)
def test_configuration_cannot_rebind_manifest(settings):
    with pytest.raises(ContractVersionError) as error:
        FakeVocalProvider(settings)
    assert error.value.detail.error_code == "MANIFEST_CONFIGURATION_CONFLICT"


def probe(data):
    source = Path(__file__).resolve().parents[1] / "src"
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("manifest_process.py"))],
        input=json.dumps(data),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
        env=dict(os.environ, PYTHONPATH=str(source), PYTHONIOENCODING="utf-8"),
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


@pytest.mark.parametrize("pair", range(10))
@pytest.mark.parametrize("mode", ["memory", "sqlite"])
def test_independent_process_manifest_pair(tmp_path, generation_payload, pair, mode):
    data = {
        "stage": "a",
        "mode": mode,
        "database": str(tmp_path / f"pair-{pair}.sqlite3"),
        "request": generation_payload,
    }
    before = probe(data)
    after = probe(
        dict(
            data,
            stage="b",
            jobs={
                v: r["job"]["job_id"]
                for v, r in before["observations"].items()
                if "job" in r
            },
        )
    )
    assert before["pid"] != after["pid"]
    assert before["finished_ns"] < after["started_ns"]
    assert before["observations"] == after["observations"]
