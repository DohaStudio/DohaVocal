"""Versioned SQLite adapter for small Fake Runtime aggregates and payload BLOBs."""

import hashlib
import json
import os
import sqlite3
import stat
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock, local

from pydantic import TypeAdapter, ValidationError

from dohavocal.artifacts.payload_memory import PayloadExpiredError, replay_conflict
from dohavocal.domain.errors import (
    ConflictError,
    InvalidStateTransitionError,
    NotFoundError,
    VocalRuntimeError,
)
from dohavocal.domain.jobs import AnyVocalJob, CreateVocalJobRequest, JobStatus
from dohavocal.domain.payloads import (
    PRIMARY_ROLES,
    AnyVocalArtifact,
    PayloadArtifact,
    PayloadContent,
    source_scope,
)
from dohavocal.providers.state import InMemoryJobStore

MAGIC = "dohavocal.runtime"
VERSION = 1
DDL = (
    "CREATE TABLE runtime_schema (magic TEXT PRIMARY KEY, version INTEGER NOT NULL)",
    (
        "CREATE TABLE jobs (job_id TEXT PRIMARY KEY, document TEXT NOT "
        "NULL, seal TEXT NOT NULL, request TEXT NOT NULL, request_seal "
        "TEXT NOT NULL, fingerprint TEXT NOT NULL, scope TEXT NOT NULL "
        "UNIQUE)"
    ),
    (
        "CREATE TABLE results (artifact_id TEXT PRIMARY KEY, job_id TEXT "
        "NOT NULL UNIQUE REFERENCES jobs(job_id), document TEXT NOT NULL, "
        "seal TEXT NOT NULL)"
    ),
    (
        "CREATE TABLE sources (source_id TEXT PRIMARY KEY, artifact_id "
        "TEXT NOT NULL UNIQUE REFERENCES results(artifact_id), job_id TEXT "
        "NOT NULL REFERENCES jobs(job_id), ordinal INTEGER NOT NULL "
        "CHECK(ordinal = 0), binding TEXT NOT NULL UNIQUE, snapshot TEXT "
        "NOT NULL, seal TEXT NOT NULL)"
    ),
    (
        "CREATE TABLE payloads (source_id TEXT PRIMARY KEY REFERENCES "
        "sources(source_id), content BLOB NOT NULL)"
    ),
)
JOB = TypeAdapter(AnyVocalJob)
RESULT = TypeAdapter(AnyVocalArtifact)


class StoreError(VocalRuntimeError):
    status_code = 503


def unavailable(code="DURABLE_STORE_UNAVAILABLE"):
    return StoreError(
        code, "Durable Runtime 저장소를 사용할 수 없습니다.", stage="persistence"
    )


def canonical(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def seal(identity, document):
    return hashlib.sha256(canonical([identity, document]).encode()).hexdigest()


def decode(adapter, identity, document, digest):
    if seal(identity, document) != digest:
        raise replay_conflict()
    try:
        value = adapter.validate_json(document)
        if canonical(value) != document:
            raise replay_conflict()
        return value
    except (ValidationError, ValueError, TypeError):
        raise replay_conflict() from None


class SQLiteRuntimeStore:
    """One short-lived connection per transaction, shared only by nested calls."""

    def __init__(
        self,
        path: Path,
        *,
        initialize=False,
        busy_timeout_ms=5000,
        failure_hook: Callable[[str], None] | None = None,
    ):
        self.path = Path(path)
        self.timeout = busy_timeout_ms
        self.failure_hook = failure_hook
        self._local = local()
        self._lifecycle = RLock()
        self._closed = False
        self.jobs = SQLiteJobStore(self)
        self.artifacts = SQLiteArtifactStore(self)
        self.payloads = SQLitePayloadStore(self)
        if not isinstance(busy_timeout_ms, int) or not 1 <= busy_timeout_ms <= 30000:
            raise unavailable("DURABLE_CONFIGURATION_INVALID")
        try:
            self._validate_path()
            created = False
            if not self.path.exists():
                if not initialize:
                    raise unavailable()
                try:
                    fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    os.close(fd)
                    created = True
                except FileExistsError:
                    pass
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                if not existing and created and self.path.stat().st_size == 0:
                    for statement in DDL:
                        connection.execute(statement)
                    connection.execute(
                        "INSERT INTO runtime_schema VALUES (?, ?)", (MAGIC, VERSION)
                    )
                self._validate_schema(connection)
                connection.commit()
        except (OSError, sqlite3.Error):
            raise unavailable() from None

    def _validate_path(self):
        if (
            not self.path.is_absolute()
            or ".." in self.path.parts
            or not self.path.parent.is_dir()
        ):
            raise unavailable("DURABLE_CONFIGURATION_INVALID")
        for part in (self.path, *self.path.parents):
            if part.exists() or part.is_symlink():
                info = part.lstat()
                if (
                    stat.S_ISLNK(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & 0x400
                ):
                    raise unavailable("DURABLE_CONFIGURATION_INVALID")
            if part.is_dir() and (part / ".git").exists():
                raise unavailable("DURABLE_CONFIGURATION_INVALID")
        if self.path.exists() and not self.path.is_file():
            raise unavailable("DURABLE_CONFIGURATION_INVALID")
        for suffix in ("-journal", "-wal", "-shm"):
            sidecar = Path(str(self.path) + suffix)
            if sidecar.exists() or sidecar.is_symlink():
                info = sidecar.lstat()
                if (
                    stat.S_ISLNK(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & 0x400
                ):
                    raise unavailable("DURABLE_CONFIGURATION_INVALID")

    @contextmanager
    def _connect(self):
        self._validate_path()
        connection = sqlite3.connect(
            self.path.as_uri() + "?mode=rw",
            uri=True,
            timeout=self.timeout / 1000,
            isolation_level=None,
        )
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute(f"PRAGMA busy_timeout={self.timeout}")
            if connection.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
                raise unavailable()
            yield connection
        finally:
            connection.close()

    def _validate_schema(self, connection):
        actual = {
            row[0]
            for row in connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='table'"
            )
        }
        if actual != set(DDL):
            raise unavailable("DURABLE_SCHEMA_INCOMPATIBLE")
        unexpected = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type NOT IN ('table', 'index') "
            "OR (type='index' AND sql IS NOT NULL)"
        ).fetchone()
        if unexpected:
            raise unavailable("DURABLE_SCHEMA_INCOMPATIBLE")
        metadata = connection.execute(
            "SELECT magic, version FROM runtime_schema"
        ).fetchall()
        if [tuple(row) for row in metadata] != [(MAGIC, VERSION)]:
            raise unavailable("DURABLE_SCHEMA_INCOMPATIBLE")
        if (
            connection.execute("PRAGMA quick_check").fetchone()[0] != "ok"
            or connection.execute("PRAGMA foreign_key_check").fetchone()
        ):
            raise unavailable("DURABLE_STORE_CORRUPT")

    @property
    def connection(self):
        return self._local.connection

    @contextmanager
    def transaction(self):
        if getattr(self._local, "connection", None) is not None:
            yield
            return
        with self._lifecycle:
            if self._closed:
                raise unavailable()
            try:
                with self._connect() as connection:
                    connection.execute("BEGIN IMMEDIATE")
                    self._local.connection = connection
                    self._local.changed = set()
                    try:
                        self._validate_schema(connection)
                        yield
                        for job_id in self._local.changed:
                            self._validate_success(self.jobs.get(job_id))
                        self.checkpoint("before_commit")
                        connection.commit()
                    except BaseException:
                        connection.rollback()
                        raise
                    finally:
                        self._local.connection = None
            except (sqlite3.Error, OSError):
                raise unavailable() from None

    def _validate_success(self, job):
        if job.status != JobStatus.SUCCEEDED:
            return
        if len(job.output_artifact_ids) != 1 or len(job.output_asset_version_ids) != 1:
            raise replay_conflict()
        result = self.artifacts.get(job.output_artifact_ids[0])
        if (
            result.run_id != job.job_id
            or result.producer_id != job.provider_id
            or result.output_asset_version_id != job.output_asset_version_ids[0]
            or result.lineage.model_manifest_id != job.model_manifest_id
            or result.lineage.settings_snapshot != job.settings_snapshot
        ):
            raise replay_conflict()
        if job.api_contract_version == "0.2.0":
            if not isinstance(result, PayloadArtifact):
                raise replay_conflict()
            if result.payloads[0].role != PRIMARY_ROLES[job.job_type]:
                raise replay_conflict()
            self.payloads.acquire(result)

    def checkpoint(self, name):
        if self.failure_hook is not None:
            self.failure_hook(name)

    def readiness(self):
        with self.transaction():
            return True

    def close(self):
        with self._lifecycle:
            self._closed = True


class SQLiteJobStore:
    def __init__(self, store):
        self.store = store

    def _row(self, job_id):
        row = self.store.connection.execute(
            "SELECT * FROM jobs WHERE job_id=?", (job_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(
                "JOB_NOT_FOUND", "Job을 찾을 수 없습니다.", stage="job_lookup"
            )
        job = decode(JOB, job_id, row["document"], row["seal"])
        request = decode(
            TypeAdapter(CreateVocalJobRequest),
            job_id,
            row["request"],
            row["request_seal"],
        )
        fingerprint = hashlib.sha256(
            canonical(
                request.model_dump(mode="json", exclude={"idempotency_key"})
            ).encode()
        ).hexdigest()
        if (
            job.job_id != job_id
            or row["fingerprint"] != fingerprint
            or row["scope"] != canonical(InMemoryJobStore.scope(request))
            or job.job_type != request.capability
            or job.provider_id != request.provider_id
            or job.api_contract_version != request.api_contract_version
            or job.model_manifest_id != request.model_manifest_id
            or job.settings_snapshot != request.settings_snapshot
        ):
            raise replay_conflict()
        return job, request

    def resolve_idempotency(self, request, fingerprint):
        with self.store.transaction():
            row = self.store.connection.execute(
                "SELECT job_id, fingerprint FROM jobs WHERE scope=?",
                (canonical(InMemoryJobStore.scope(request)),),
            ).fetchone()
            if row is None:
                return None
            job, _ = self._row(row["job_id"])
            if row["fingerprint"] != fingerprint:
                raise ConflictError(
                    "IDEMPOTENCY_CONFLICT",
                    "같은 idempotency key가 다른 요청에 사용되었습니다.",
                    stage="job_creation",
                )
            return job

    def add(self, job, request, fingerprint):
        with self.store.transaction():
            existing = self.resolve_idempotency(request, fingerprint)
            if existing is not None:
                return existing
            document, request_json = canonical(job), canonical(request)
            self.store.connection.execute(
                "INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    job.job_id,
                    document,
                    seal(job.job_id, document),
                    request_json,
                    seal(job.job_id, request_json),
                    fingerprint,
                    canonical(InMemoryJobStore.scope(request)),
                ),
            )
            self.store._local.changed.add(job.job_id)
            return None

    def get(self, job_id):
        with self.store.transaction():
            return self._row(job_id)[0]

    def get_request(self, job_id):
        with self.store.transaction():
            return self._row(job_id)[1]

    def replace(self, job):
        with self.store.transaction():
            self.get(job.job_id)
            document = canonical(job)
            self.store.connection.execute(
                "UPDATE jobs SET document=?, seal=? WHERE job_id=?",
                (document, seal(job.job_id, document), job.job_id),
            )
            self.store._local.changed.add(job.job_id)

    def replace_if_status(self, job, expected_status):
        with self.store.transaction():
            if self.get(job.job_id).status != expected_status:
                raise InvalidStateTransitionError(
                    "STATE_TRANSITION_INVALID",
                    "동시에 변경된 Job 상태에서는 전이할 수 없습니다.",
                    stage="state_transition",
                )
            self.replace(job)
            return job

    def count(self):
        with self.store.transaction():
            return self.store.connection.execute(
                "SELECT COUNT(*) FROM jobs"
            ).fetchone()[0]


class SQLiteArtifactStore:
    def __init__(self, store):
        self.store = store

    def add(self, artifact):
        with self.store.transaction():
            document = canonical(artifact)
            self.store.connection.execute(
                "INSERT INTO results VALUES (?, ?, ?, ?)",
                (
                    artifact.artifact_id,
                    artifact.run_id,
                    document,
                    seal(artifact.artifact_id, document),
                ),
            )

    def get(self, artifact_id):
        with self.store.transaction():
            row = self.store.connection.execute(
                "SELECT * FROM results WHERE artifact_id=?", (artifact_id,)
            ).fetchone()
            if row is None:
                raise NotFoundError(
                    "ARTIFACT_NOT_FOUND",
                    "Artifact를 찾을 수 없습니다.",
                    stage="result_lookup",
                )
            result = decode(RESULT, artifact_id, row["document"], row["seal"])
            if result.artifact_id != artifact_id or result.run_id != row["job_id"]:
                raise replay_conflict()
            return result

    def count(self):
        with self.store.transaction():
            return self.store.connection.execute(
                "SELECT COUNT(*) FROM results"
            ).fetchone()[0]


class SQLitePayloadStore:
    def __init__(self, store):
        self.store = store

    def add(self, result, content):
        with self.store.transaction():
            entry = result.payloads[0]
            if (
                len(content) != entry.expected_size_bytes
                or hashlib.sha256(content).hexdigest() != entry.payload_checksum
            ):
                raise replay_conflict()
            self.store.checkpoint("before_descriptor")
            snapshot = canonical(result)
            self.store.connection.execute(
                "INSERT INTO sources VALUES (?, ?, ?, 0, ?, ?, ?)",
                (
                    entry.source.source_id,
                    result.artifact_id,
                    result.run_id,
                    canonical(source_scope(result)),
                    snapshot,
                    seal(entry.source.source_id, snapshot),
                ),
            )
            self.store.checkpoint("after_descriptor")
            cursor = self.store.connection.execute(
                "INSERT INTO payloads VALUES (?, zeroblob(?))",
                (entry.source.source_id, len(content)),
            )
            with self.store.connection.blobopen(
                "payloads", "content", cursor.lastrowid
            ) as blob:
                middle = len(content) // 2
                blob.write(content[:middle])
                self.store.checkpoint("during_payload_write")
                blob.write(content[middle:])
            self.store.checkpoint("after_payload_blob")

    def verify_result(self, result):
        with self.store.transaction():
            entry = result.payloads[0]
            row = self.store.connection.execute(
                "SELECT * FROM sources WHERE source_id=?", (entry.source.source_id,)
            ).fetchone()
            if row is None or (
                row["artifact_id"],
                row["job_id"],
                row["ordinal"],
                row["binding"],
            ) != (
                result.artifact_id,
                result.run_id,
                0,
                canonical(source_scope(result)),
            ):
                raise replay_conflict()
            snapshot = decode(
                TypeAdapter(PayloadArtifact),
                entry.source.source_id,
                row["snapshot"],
                row["seal"],
            )
            if snapshot != result:
                raise replay_conflict()
            self._read_content(result)

    def _read_content(self, result):
        entry = result.payloads[0]
        row = self.store.connection.execute(
            "SELECT content FROM payloads WHERE source_id=?",
            (entry.source.source_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError(
                "PROVIDER_PAYLOAD_UNAVAILABLE",
                "Payload를 제공할 수 없습니다.",
                stage="payload_acquisition",
            )
        content = row[0]
        if (
            not isinstance(content, bytes)
            or len(content) != entry.expected_size_bytes
            or hashlib.sha256(content).hexdigest() != entry.payload_checksum
        ):
            raise replay_conflict()
        return content

    def acquire(self, result):
        with self.store.transaction():
            self.verify_result(result)
            entry = result.payloads[0]
            if (
                entry.available_until is not None
                and entry.available_until <= datetime.now(UTC)
            ):
                raise PayloadExpiredError(
                    "PROVIDER_PAYLOAD_EXPIRED",
                    "Payload 제공 기간이 종료되었습니다.",
                    stage="payload_acquisition",
                )
            content = self._read_content(result)
            return PayloadContent(content, entry.expected_media_type)

    def contains_source(self, source_id):
        with self.store.transaction():
            return (
                self.store.connection.execute(
                    "SELECT 1 FROM sources WHERE source_id=?", (source_id,)
                ).fetchone()
                is not None
            )

    def count(self):
        with self.store.transaction():
            return self.store.connection.execute(
                "SELECT COUNT(*) FROM payloads"
            ).fetchone()[0]
