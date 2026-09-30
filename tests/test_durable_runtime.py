"""Durable identity, atomic publication, recovery and fail-closed acceptance."""

import json
import os
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dohavocal.api.app import create_app
from dohavocal.config import RuntimeSettings
from dohavocal.domain.errors import VocalRuntimeError
from dohavocal.domain.jobs import JobStatus, JobType
from dohavocal.persistence.sqlite import SQLiteRuntimeStore
from dohavocal.providers.fake import FakeVocalProvider
from dohavocal.runtime.composition import build_provider


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    SQLiteRuntimeStore(path, initialize=True).close()
    return path


def configured(db):
    return RuntimeSettings(runtime_mode="sqlite", database_path=db)


def payload_request(factory, kind=JobType.VOCAL_GENERATION, version="0.2.0", **kwargs):
    request = factory(kind, **kwargs)
    return request.model_copy(
        update={
            "api_contract_version": version,
            "model_manifest_id": "dohavocal.fake-model@" + version,
        }
    )


def worker(db, request, mode, job_id=None):
    env = dict(
        os.environ,
        PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
        PYTHONIOENCODING="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("durable_process.py"))],
        input=json.dumps(
            {
                "database": str(db),
                "request": request.model_dump(mode="json"),
                "mode": mode,
                "job_id": job_id,
            }
        ),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


@pytest.mark.parametrize("kind", list(JobType))
@pytest.mark.parametrize("version", ["0.1.0", "0.2.0"])
@pytest.mark.parametrize("mode", ["create", "abrupt"])
def test_independent_process_restart(db, request_factory, kind, version, mode):
    request = payload_request(request_factory, kind, version)
    before = worker(db, request, mode)
    after = worker(db, request, "reopen", before["job"]["job_id"])
    assert before == after
    provider = build_provider(configured(db))
    assert provider.jobs.count() == provider.artifacts.count() == 1
    assert provider.payloads.count() == (1 if version == "0.2.0" else 0)
    provider.close()


@pytest.mark.parametrize("outcome", ["queued", "running", "failed", "cancelled"])
def test_inflight_and_retry_restart(db, request_factory, outcome):
    provider = build_provider(configured(db))
    request = payload_request(
        request_factory,
        settings={"fake_outcome": "queued" if outcome == "cancelled" else outcome},
    )
    job = provider.create_job(request)
    if outcome == "cancelled":
        job = provider.cancel_job(job.job_id)
    provider.close()
    reopened = build_provider(configured(db))
    assert reopened.get_job_status(job.job_id) == job
    assert reopened.create_job(request) == job
    if outcome in ("queued", "running"):
        job = reopened.cancel_job(job.job_id)
    retry = reopened.retry_job(job.job_id)
    reopened.close()
    again = build_provider(configured(db))
    assert again.get_job_status(job.job_id) == job
    assert again.get_job_status(retry.job_id) == retry
    assert retry.retry_of_job_id == job.job_id
    again.close()


FAULTS = [
    "before_job_insert",
    "after_job_insert",
    "before_running",
    "after_running",
    "before_result_insert",
    "after_result_insert",
    "before_descriptor",
    "after_descriptor",
    "during_payload_write",
    "after_payload_blob",
    "before_succeeded",
    "before_commit",
]


@pytest.mark.parametrize("point", FAULTS)
def test_atomic_rollback(db, request_factory, point):
    def fail(name):
        if name == point:
            raise RuntimeError("injected publication interruption")

    store = SQLiteRuntimeStore(db, failure_hook=fail)
    provider = FakeVocalProvider(
        configured(db), store.jobs, store.artifacts, store.payloads, store
    )
    with pytest.raises(RuntimeError, match="injected"):
        provider.create_job(payload_request(request_factory))
    provider.close()
    reopened = SQLiteRuntimeStore(db)
    with sqlite3.connect(db) as conn:
        assert [
            conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
            for table in ("jobs", "results", "sources", "payloads")
        ] == [0, 0, 0, 0]
    reopened.close()


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE results SET seal='broken'",
        "UPDATE results SET document=replace(document, 'audio/wav', 'audio/flac')",
        "UPDATE sources SET binding='broken'",
        "UPDATE sources SET snapshot='{}'",
        "UPDATE payloads SET content=x'0001'",
        "DELETE FROM payloads",
        "UPDATE jobs SET fingerprint='broken'",
        "UPDATE jobs SET request_seal='broken'",
    ],
)
def test_corruption_no_regeneration(db, request_factory, monkeypatch, sql):
    provider = build_provider(configured(db))
    job = provider.create_job(payload_request(request_factory))
    result = provider.get_result(job.job_id)
    provider.close()
    with sqlite3.connect(db) as conn:
        conn.execute(sql)

    def forbidden(*args):
        pytest.fail("silent regeneration")

    monkeypatch.setattr(FakeVocalProvider, "_with_payload", forbidden)
    reopened = build_provider(configured(db))
    with pytest.raises(VocalRuntimeError):
        reopened.get_payload_content(
            job.job_id, result.artifact_id, result.payloads[0].source.source_id
        )
    with sqlite3.connect(db) as conn:
        stored = json.loads(conn.execute("SELECT document FROM jobs").fetchone()[0])
        assert stored == job.model_dump(mode="json")
    reopened.close()


def test_cross_process_idempotency(db, request_factory):
    request = payload_request(request_factory)
    with ThreadPoolExecutor(max_workers=4) as pool:
        outputs = list(pool.map(lambda _: worker(db, request, "create"), range(4)))
    assert all(output == outputs[0] for output in outputs)
    store = SQLiteRuntimeStore(db)
    assert store.jobs.count() == store.artifacts.count() == store.payloads.count() == 1
    store.close()


def test_concurrent_conflicting_fingerprint(db, request_factory):
    first = payload_request(request_factory, idempotency_key="shared")
    second = first.model_copy(update={"settings_snapshot": {"different": True}})

    def create(request):
        provider = build_provider(configured(db))
        try:
            return provider.create_job(request).job_id
        except VocalRuntimeError as exc:
            return exc.detail.error_code
        finally:
            provider.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, [first, second]))
    assert results.count("IDEMPOTENCY_CONFLICT") == 1


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE runtime_schema SET version=99",
        "UPDATE runtime_schema SET magic='other'",
        "ALTER TABLE jobs ADD COLUMN unknown TEXT",
        "DROP TABLE payloads",
    ],
)
def test_schema_fail_closed(db, sql):
    with sqlite3.connect(db) as conn:
        conn.execute(sql)
    before = db.read_bytes()
    with pytest.raises(VocalRuntimeError):
        SQLiteRuntimeStore(db)
    assert db.read_bytes() == before


def test_malformed_and_missing_database(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    with pytest.raises(VocalRuntimeError):
        SQLiteRuntimeStore(path)
    assert not path.exists()
    path.write_bytes(b"not a database")
    with pytest.raises(VocalRuntimeError):
        SQLiteRuntimeStore(path, initialize=True)
    assert path.read_bytes() == b"not a database"


def test_readiness_failure_and_shutdown(db):
    provider = build_provider(configured(db))
    assert provider.health() and provider.readiness()
    db.unlink()
    with pytest.raises(VocalRuntimeError):
        provider.readiness()
    assert not db.exists()
    assert provider.health()
    provider.close()
    with pytest.raises(VocalRuntimeError):
        provider.readiness()


def test_api_readiness_safe_error(db):
    with TestClient(create_app(settings=configured(db))) as client:
        assert client.get("/ready").status_code == 200
        db.unlink()
        response = client.get("/ready")
        assert response.status_code == 503
        assert str(db) not in response.text
        assert client.get("/health").status_code == 200


def test_lock_timeout(db, request_factory):
    store = SQLiteRuntimeStore(db, busy_timeout_ms=25)
    provider = FakeVocalProvider(
        configured(db), store.jobs, store.artifacts, store.payloads, store
    )
    with sqlite3.connect(db) as blocker:
        blocker.execute("BEGIN IMMEDIATE")
        with pytest.raises(VocalRuntimeError) as error:
            provider.create_job(payload_request(request_factory))
        assert error.value.detail.error_code == "DURABLE_STORE_UNAVAILABLE"
    assert store.jobs.count() == 0
    store.close()


@pytest.mark.parametrize(
    "kind",
    [
        "relative",
        "file_parent",
        "directory",
        "repository",
        "invalid_mode",
        "inconsistent",
    ],
)
def test_configuration_boundary(tmp_path, kind):
    path = tmp_path / "runtime.sqlite3"
    mode = "sqlite"
    if kind == "relative":
        path = Path("runtime.sqlite3")
    elif kind == "file_parent":
        path.write_text("file")
        path = path / "db"
    elif kind == "directory":
        path.mkdir()
    elif kind == "repository":
        path = Path(__file__).resolve().parents[1] / "runtime.sqlite3"
    elif kind == "invalid_mode":
        mode = "unknown"
    else:
        mode = "memory"
    with pytest.raises(VocalRuntimeError):
        build_provider(
            RuntimeSettings(
                runtime_mode=mode, database_path=path, initialize_database=True
            )
        )


@pytest.mark.parametrize(
    "key",
    [
        "Authorization",
        "cookie",
        "access_token",
        "refresh_token",
        "signed_url",
        "credentials",
    ],
)
def test_credentials_rejected_before_persistence(db, request_factory, key):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        request_factory(settings={key: "synthetic-secret"})
    store = SQLiteRuntimeStore(db)
    assert store.jobs.count() == 0
    store.close()


def test_symlink_storage_rejected(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(target, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        # Windows junction is a reparse point and needs no symlink privilege.
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(alias), str(target)], capture_output=True
        )
        assert result.returncode == 0
    with pytest.raises(VocalRuntimeError):
        SQLiteRuntimeStore(alias / "runtime.sqlite3", initialize=True)
    assert not (target / "runtime.sqlite3").exists()


def test_database_permissions_and_pragmas(db):
    store = SQLiteRuntimeStore(db)
    with store.transaction():
        values = [
            store.connection.execute("PRAGMA " + name).fetchone()[0]
            for name in ("foreign_keys", "journal_mode", "synchronous", "busy_timeout")
        ]
        assert values == [1, "delete", 2, 5000]
    if os.name != "nt":
        assert db.stat().st_mode & 0o777 == 0o600
    store.close()


def test_succeeded_requires_complete_aggregate(db, request_factory):
    store = SQLiteRuntimeStore(db)
    provider = FakeVocalProvider(
        configured(db), store.jobs, store.artifacts, store.payloads, store
    )
    job = provider.create_job(
        payload_request(request_factory, settings={"fake_outcome": "running"})
    )
    with pytest.raises(VocalRuntimeError):
        provider.transition(
            job.job_id,
            JobStatus.SUCCEEDED,
            output_asset_version_ids=("missing",),
            output_artifact_ids=("missing",),
        )
    assert provider.get_job_status(job.job_id) == job
    provider.close()


def test_abrupt_uncommitted_transaction(db, request_factory):
    request = payload_request(request_factory)
    script = """
import json, os, sys
from pathlib import Path
from dohavocal.persistence.sqlite import SQLiteRuntimeStore
from dohavocal.providers import FakeVocalProvider
from dohavocal.domain.jobs import CreateVocalJobRequest
args=json.load(sys.stdin)
def fail(name):
    if name == 'before_commit':
        os._exit(73)
store=SQLiteRuntimeStore(Path(args['db']), failure_hook=fail)
provider=FakeVocalProvider(
    jobs=store.jobs, artifacts=store.artifacts,
    payloads=store.payloads, unit_of_work=store)
provider.create_job(CreateVocalJobRequest.model_validate(args['request']))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        input=json.dumps({"db": str(db), "request": request.model_dump(mode="json")}),
        text=True,
        capture_output=True,
        timeout=30,
        env=dict(
            os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src")
        ),
    )
    assert completed.returncode == 73, completed.stderr
    store = SQLiteRuntimeStore(db)
    assert store.jobs.count() == store.artifacts.count() == store.payloads.count() == 0
    store.close()


def test_existing_empty_database_is_not_bootstrapped(tmp_path):
    path = tmp_path / "runtime.sqlite3"
    path.touch()
    with pytest.raises(VocalRuntimeError):
        SQLiteRuntimeStore(path, initialize=True)
    assert path.read_bytes() == b""


@pytest.mark.parametrize(
    "value",
    [
        "Bearer synthetic-token",
        "https://example.invalid/file?token=synthetic",
        "https://example.invalid/file?X-Amz-Signature=synthetic",
    ],
)
def test_credential_values_rejected(request_factory, value):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        request_factory(settings={"reference": value})


def test_cli_memory_and_durable(tmp_path, monkeypatch):
    import uvicorn

    from dohavocal.runtime.main import main

    observed = []

    def serve(app, **kwargs):
        with TestClient(app) as client:
            observed.append(client.get("/ready").status_code)

    monkeypatch.setattr(uvicorn, "run", serve)
    monkeypatch.setattr(sys, "argv", ["dohavocal"])
    main()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dohavocal",
            "--runtime-mode",
            "sqlite",
            "--database",
            str(tmp_path / "cli.sqlite3"),
            "--initialize-database",
        ],
    )
    main()
    assert observed == [200, 200]


def test_same_size_corrupt_blob_fail_closed(db, request_factory):
    provider = build_provider(configured(db))
    job = provider.create_job(payload_request(request_factory))
    result = provider.get_result(job.job_id)
    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE payloads SET content=zeroblob(?)", (result.size_bytes,)
        )
    with pytest.raises(VocalRuntimeError):
        provider.get_result(job.job_id)
    assert provider.get_job_status(job.job_id) == job
    provider.close()
