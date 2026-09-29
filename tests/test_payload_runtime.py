"""Executable 0.2.0 contract without network, user audio or models."""

import asyncio
import hashlib
import io
import json
import wave
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import pytest
from pydantic import TypeAdapter, ValidationError

from dohavocal.api.app import create_app
from dohavocal.application import VocalRuntimeService
from dohavocal.artifacts.payload_memory import InMemoryPayloadStore, PayloadExpiredError
from dohavocal.domain.errors import ConflictError, VocalRuntimeError
from dohavocal.domain.jobs import JobStatus, JobType
from dohavocal.domain.payloads import (
    MetadataPayloadArtifact,
    PayloadArtifact,
    PayloadSource,
    source_scope,
)

ROLES = {
    JobType.VOCAL_GENERATION: "generated_vocal_candidate",
    JobType.VOICE_CONVERSION: "converted_vocal_candidate",
    JobType.VOCAL_CORRECTION: "corrected_vocal_candidate",
    JobType.VOCAL_ANALYSIS: "vocal_analysis_result",
}


@pytest.fixture
def payload_request(request_factory):
    def make(kind=JobType.VOCAL_GENERATION, **kwargs):
        return request_factory(kind, **kwargs).model_copy(
            update={
                "api_contract_version": "0.2.0",
                "model_manifest_id": "dohavocal.fake-model@0.2.0",
            }
        )

    return make


def path(job_id, entry):
    return (
        f"/v1/jobs/{job_id}/artifacts/{entry.provider_artifact_id}"
        f"/payloads/{entry.source.source_id}"
    )


def test_version_negotiation_and_exact_capabilities(client, provider, payload_request):
    old = client.get("/v1/capabilities").json()
    assert old["api_contract_version"] == "0.1.0"
    assert set(old) == {
        "provider_id",
        "api_contract_version",
        "capabilities",
        "supported_operations",
    }
    assert old["supported_operations"] == [
        "GetCapabilities",
        "CreateJob",
        "GetJobStatus",
        "CancelJob",
        "RetryJob",
        "GetResult",
        "GetModelManifest",
        "Health",
        "Readiness",
    ]
    new = client.get("/v1/capabilities?api_contract_version=0.2.0").json()
    assert new["supported_operations"] == [
        *old["supported_operations"],
        "GetPayloadContent",
    ]
    assert new["payload_acquisition"] == {
        "supported": True,
        "source_kinds": ["provider_subresource"],
        "operation": "GetPayloadContent",
    }
    assert new["api_contract_version"] == "0.2.0"
    assert new["capabilities"] == old["capabilities"]
    assert client.get("/v1/capabilities?api_contract_version=9").status_code == 400
    bad = payload_request().model_copy(
        update={"model_manifest_id": "dohavocal.fake-model@0.1.0"}
    )
    assert client.post("/v1/jobs", json=bad.model_dump(mode="json")).status_code == 404
    manifest = client.get("/v1/model-manifests/dohavocal.fake-model@0.2.0").json()
    assert manifest["api_contract_version"] == "0.2.0"
    assert manifest["output_formats"] == ["audio/wav", "application/json"]
    assert manifest["runtime_environment"]["persistence"] == "process-local"
    assert provider.payloads.count() == 0


def test_legacy_result_shape_remains_strict(client, generation_payload, provider):
    job = client.post("/v1/jobs", json=generation_payload).json()
    result = client.get(f"/v1/jobs/{job['job_id']}/result").json()
    assert set(result) == {
        "artifact_id",
        "artifact_kind",
        "media_type",
        "size_bytes",
        "checksum_algorithm",
        "artifact_checksum",
        "checksum_scope",
        "payload_present",
        "producer_type",
        "producer_id",
        "run_id",
        "retention_status",
        "output_asset_version_id",
        "lineage",
        "analysis_result",
    }
    assert result["payload_present"] is False
    assert result["size_bytes"] == 0
    assert result["checksum_scope"] == "metadata_descriptor"
    response = client.get(
        f"/v1/jobs/{job['job_id']}/artifacts/{result['artifact_id']}/payloads/opaque"
    )
    assert response.json()["error"]["error_code"] == "CONTRACT_VERSION_UNSUPPORTED"
    assert provider.payloads.count() == 0


@pytest.mark.parametrize("kind", list(JobType))
def test_bytes_role_integrity_replay_and_lineage(
    client, provider, payload_request, kind
):
    request = payload_request(kind)
    created = client.post("/v1/jobs", json=request.model_dump(mode="json"))
    assert created.status_code == 201
    job = created.json()
    response = client.get(f"/v1/jobs/{job['job_id']}/result")
    result = PayloadArtifact.model_validate(response.json())
    (entry,) = result.payloads
    assert entry.role == ROLES[kind]
    assert source_scope(result) == (
        "dohavocal",
        job["job_id"],
        result.artifact_id,
        ROLES[kind],
        entry.source.source_id,
    )
    assert result.lineage.model_manifest_id == request.model_manifest_id
    assert result.lineage.settings_snapshot == request.settings_snapshot
    assert result.lineage.source_artifact_id == request.input_artifact_ids[0]
    if kind != JobType.VOCAL_GENERATION:
        assert (
            result.lineage.source_asset_version_id
            == request.job_input.source_asset_version_id
        )
        assert (
            result.lineage.parent_asset_version_id
            == request.job_input.source_asset_version_id
        )
    wire = client.get(path(job["job_id"], entry), follow_redirects=False)
    assert wire.status_code == 200
    assert "location" not in wire.headers
    assert "content-encoding" not in wire.headers
    assert wire.headers["content-type"] == entry.expected_media_type
    assert (
        int(wire.headers["content-length"])
        == len(wire.content)
        == entry.expected_size_bytes
    )
    assert hashlib.sha256(wire.content).hexdigest() == entry.payload_checksum
    assert entry.payload_checksum != result.artifact_checksum
    assert result.artifact_checksum == result.lineage.checksum
    assert result.checksum_scope == "metadata_descriptor"
    if kind == JobType.VOCAL_ANALYSIS:
        assert (
            wire.content
            == json.dumps(
                result.analysis_result, sort_keys=True, separators=(",", ":")
            ).encode()
        )
    else:
        assert wire.content.startswith(b"RIFF")
        with wave.open(io.BytesIO(wire.content)) as wav:
            assert (
                wav.getnchannels(),
                wav.getsampwidth(),
                wav.getframerate(),
                wav.getnframes(),
            ) == (1, 2, 8000, 800)
            assert wav.readframes(800) == bytes(1600)
    for _ in range(3):
        assert client.get(path(job["job_id"], entry)).content == wire.content
        assert (
            client.get(f"/v1/jobs/{job['job_id']}/result").content == response.content
        )
        assert client.get(f"/v1/jobs/{job['job_id']}").json() == job
    second = provider.create_job(payload_request(kind))
    other = provider.get_result(second.job_id).payloads[0]
    assert other.payload_checksum == entry.payload_checksum
    assert other.source.source_id != entry.source.source_id
    assert other.provider_artifact_id != entry.provider_artifact_id


@pytest.mark.parametrize("present,count", [(False, 1), (True, 0), (True, 2)])
def test_presence_and_duplicate_schema_rejection(
    provider, payload_request, present, count
):
    job = provider.create_job(payload_request())
    raw = provider.get_result(job.job_id).model_dump()
    raw["payload_present"] = present
    raw["payloads"] = raw["payloads"] * count
    with pytest.raises(ValidationError):
        TypeAdapter(PayloadArtifact | MetadataPayloadArtifact).validate_python(raw)


def test_metadata_variant_schema(provider, payload_request):
    job = provider.create_job(payload_request())
    raw = provider.get_result(job.job_id).model_dump()
    raw.update(payload_present=False, payloads=[])
    assert MetadataPayloadArtifact.model_validate(raw).payloads == ()
    assert (
        PayloadArtifact.model_json_schema()["properties"]["payloads"]["minItems"] == 1
    )
    assert (
        MetadataPayloadArtifact.model_json_schema()["properties"]["payloads"][
            "maxItems"
        ]
        == 0
    )


@pytest.mark.parametrize(
    "mutation",
    ["role", "media", "artifact", "provider", "job", "size", "checksum", "expiry"],
)
def test_malformed_descriptors_fail_closed(provider, payload_request, mutation):
    job = provider.create_job(payload_request())
    raw = provider.get_result(job.job_id).model_dump(mode="json")
    entry = raw["payloads"][0]
    if mutation == "role":
        entry["role"] = "auxiliary"
    elif mutation == "media":
        entry["expected_media_type"] = "application/json"
    elif mutation == "artifact":
        entry["provider_artifact_id"] = "another-artifact"
    elif mutation == "provider":
        raw["producer_id"] = "another-provider"
    elif mutation == "job":
        raw["run_id"] = "another-job"
    elif mutation == "size":
        entry["expected_size_bytes"] = 0
    elif mutation == "checksum":
        entry["payload_checksum"] = "A" * 64
    elif mutation == "expiry":
        entry["available_until"] = "2026-01-01T00:00:00"
    with pytest.raises(ValidationError):
        PayloadArtifact.model_validate(raw)


@pytest.mark.parametrize(
    "field", ["role", "source", "checksum", "manifest", "lineage", "availability"]
)
def test_replay_conflict_on_corrupted_stored_result(provider, payload_request, field):
    job = provider.create_job(payload_request())
    result = provider.get_result(job.job_id)
    entry = result.payloads[0]
    if field == "role":
        entry = entry.model_copy(update={"role": "converted_vocal_candidate"})
    elif field == "source":
        entry = entry.model_copy(
            update={"source": PayloadSource(source_id="replacement")}
        )
    elif field == "checksum":
        entry = entry.model_copy(update={"payload_checksum": "0" * 64})
    elif field == "availability":
        entry = entry.model_copy(update={"available_until": datetime.now(UTC)})
    elif field == "manifest":
        result = result.model_copy(
            update={
                "lineage": result.lineage.model_copy(
                    update={"model_manifest_id": "other"}
                )
            }
        )
    elif field == "lineage":
        result = result.model_copy(
            update={
                "lineage": result.lineage.model_copy(
                    update={"source_asset_version_id": "other"}
                )
            }
        )
    result = result.model_copy(update={"payloads": (entry,)})
    provider.artifacts._items[result.artifact_id] = result
    with pytest.raises(ConflictError) as caught:
        provider.get_result(job.job_id)
    assert caught.value.detail.error_code == "PROVIDER_RESULT_REPLAY_CONFLICT"
    assert provider.get_job_status(job.job_id) == job


def test_exact_job_artifact_source_binding(client, provider, payload_request):
    a = provider.create_job(payload_request())
    b = provider.create_job(payload_request())
    ea = provider.get_result(a.job_id).payloads[0]
    eb = provider.get_result(b.job_id).payloads[0]
    cases = [
        ("missing", ea.provider_artifact_id, ea.source.source_id, "JOB_NOT_FOUND"),
        (
            a.job_id,
            eb.provider_artifact_id,
            ea.source.source_id,
            "PROVIDER_PAYLOAD_ARTIFACT_MISMATCH",
        ),
        (
            a.job_id,
            ea.provider_artifact_id,
            eb.source.source_id,
            "PROVIDER_PAYLOAD_SOURCE_BINDING_MISMATCH",
        ),
        (
            a.job_id,
            ea.provider_artifact_id,
            "unknown",
            "PROVIDER_PAYLOAD_SOURCE_NOT_FOUND",
        ),
    ]
    for jid, aid, sid, code in cases:
        response = client.get(f"/v1/jobs/{jid}/artifacts/{aid}/payloads/{sid}")
        assert response.status_code == 404
        assert response.json()["error"]["error_code"] == code
    assert provider.get_job_status(a.job_id) == a
    assert provider.get_job_status(b.job_id) == b


BAD_IDS = [
    "../",
    "..\\",
    "/tmp/private",
    "C:\\private",
    "\\\\host\\share",
    "file://private",
    "http://private",
    "https://private",
    "data:private",
    "?token=private",
    "#fragment",
    "%2Fprivate",
    "%252Fprivate",
    "%3Ftoken%3Dprivate",
    "Bearer private",
    "key=value",
    "a..b",
    "é",
    "a" * 201,
    "",
    "bucket/object",
]


@pytest.mark.parametrize("value", BAD_IDS)
def test_source_injection_rejected_without_echo(
    client, provider, payload_request, value
):
    with pytest.raises(ValidationError):
        PayloadSource(source_id=value)
    job = provider.create_job(payload_request())
    entry = provider.get_result(job.job_id).payloads[0]
    with pytest.raises(VocalRuntimeError) as caught:
        provider.get_payload_content(job.job_id, entry.provider_artifact_id, value)
    assert caught.value.detail.error_code == "PROVIDER_PAYLOAD_INVALID_SOURCE_IDENTITY"
    endpoint = path(job.job_id, entry).rsplit("/", 1)[0] + "/" + quote(value, safe="")
    response = client.get(endpoint, follow_redirects=False)
    assert response.status_code in {400, 404}
    assert "location" not in response.headers
    assert "private" not in response.text
    assert "Traceback" not in response.text
    assert provider.get_job_status(job.job_id) == job


@pytest.mark.parametrize(
    "value", ["a", "0", "opaque-stable-source-id", "tokenizer-v1", "A_b.c-2", "x" * 200]
)
def test_normal_opaque_ids_accepted(value):
    assert PayloadSource(source_id=value).source_id == value


def test_query_role_range_and_redirect_rejected(client, provider, payload_request):
    job = provider.create_job(payload_request())
    entry = provider.get_result(job.job_id).payloads[0]
    endpoint = path(job.job_id, entry)
    for suffix in ["?role=converted_vocal_candidate", "?token=private", "/"]:
        response = client.get(endpoint + suffix, follow_redirects=False)
        assert response.status_code == 400
        assert "location" not in response.headers
    assert client.get(endpoint, headers={"Range": "bytes=0-1"}).status_code == 400
    assert (
        client.get(endpoint, headers={"Accept-Encoding": "gzip"}).headers.get(
            "content-encoding"
        )
        is None
    )


@pytest.mark.parametrize("outcome", ["queued", "running", "failed"])
def test_unavailable_result_does_not_mutate_job(
    client, provider, payload_request, outcome
):
    job = provider.create_job(payload_request(settings={"fake_outcome": outcome}))
    response = client.get(f"/v1/jobs/{job.job_id}/artifacts/opaque/payloads/opaque")
    assert response.status_code == 409
    assert response.json()["error"]["error_code"] == "JOB_RESULT_NOT_AVAILABLE"
    assert provider.get_job_status(job.job_id) == job
    assert provider.payloads.count() == 0


def test_missing_expired_and_corrupt_bytes(provider, payload_request):
    job = provider.create_job(payload_request())
    result = provider.get_result(job.job_id)
    entry = result.payloads[0]
    content = provider.payloads.acquire(result).content
    expired = result.model_copy(
        update={
            "payloads": (
                entry.model_copy(
                    update={"available_until": datetime.now(UTC) - timedelta(seconds=1)}
                ),
            )
        }
    )
    store = InMemoryPayloadStore()
    store.add(expired, content)
    with pytest.raises(PayloadExpiredError) as caught:
        store.acquire(expired)
    assert caught.value.detail.error_code == "PROVIDER_PAYLOAD_EXPIRED"
    provider.payloads._content[source_scope(result)] = b"corrupted"
    with pytest.raises(ConflictError):
        provider.get_payload_content(
            job.job_id, entry.provider_artifact_id, entry.source.source_id
        )
    del provider.payloads._content[source_scope(result)]
    with pytest.raises(VocalRuntimeError) as caught:
        provider.get_payload_content(
            job.job_id, entry.provider_artifact_id, entry.source.source_id
        )
    assert caught.value.detail.error_code == "PROVIDER_PAYLOAD_UNAVAILABLE"
    assert provider.get_result(job.job_id) == result
    assert provider.get_job_status(job.job_id) == job


def test_idempotency_concurrency_and_retry(provider, payload_request):
    request = payload_request(idempotency_key="payload-replay")
    with ThreadPoolExecutor(max_workers=8) as executor:
        jobs = list(executor.map(lambda _: provider.create_job(request), range(20)))
    assert len({job.job_id for job in jobs}) == 1
    job = provider.get_job_status(jobs[0].job_id)
    result = provider.get_result(job.job_id)
    assert provider.create_job(request) == job
    assert provider.get_result(job.job_id) == result
    assert (
        provider.jobs.count(),
        provider.artifacts.count(),
        provider.payloads.count(),
    ) == (1, 1, 1)
    with pytest.raises(ConflictError):
        provider.create_job(
            request.model_copy(update={"settings_snapshot": {"different": True}})
        )
    with pytest.raises(ConflictError):
        provider.retry_job(job.job_id)
    failed = provider.create_job(payload_request(settings={"fake_outcome": "failed"}))
    retry = provider.retry_job(failed.job_id)
    assert retry.job_id != failed.job_id
    assert retry.retry_of_job_id == failed.job_id
    assert retry.api_contract_version == "0.2.0"
    assert provider.get_job_status(failed.job_id) == failed
    assert provider.payloads.count() == 1


def test_returned_copy_cannot_change_replay(provider, payload_request):
    job = provider.create_job(payload_request(settings={"nested": {"value": 1}}))
    expected = provider.get_result(job.job_id)
    detached = provider.get_result(job.job_id)
    detached.lineage.settings_snapshot["nested"]["value"] = 99
    assert provider.get_result(job.job_id) == expected


def test_real_asgi_disconnect_leaves_job_and_result_unchanged(
    provider, payload_request
):
    job = provider.create_job(payload_request())
    result = provider.get_result(job.job_id)
    endpoint = path(job.job_id, result.payloads[0])
    app = create_app(VocalRuntimeService(provider))

    async def transfer():
        sent = []
        disconnected = asyncio.Event()
        initial = True

        async def receive():
            nonlocal initial
            if initial:
                initial = False
                return {"type": "http.request", "body": b"", "more_body": False}
            await disconnected.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            sent.append(message)
            if message["type"] == "http.response.body" and message.get("body"):
                disconnected.set()
                await asyncio.sleep(0)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": endpoint,
            "raw_path": endpoint.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [],
            "server": ("testserver", 80),
            "client": ("testclient", 1),
        }
        await asyncio.wait_for(app(scope, receive, send), timeout=5)
        return sent

    sent = asyncio.run(transfer())
    bodies = [item["body"] for item in sent if item["type"] == "http.response.body"]
    received = b"".join(bodies)
    entry = result.payloads[0]
    assert 0 < len(received) < entry.expected_size_bytes
    assert provider.get_job_status(job.job_id) == job
    assert job.status == JobStatus.SUCCEEDED
    assert provider.get_result(job.job_id) == result
    retried = provider.get_payload_content(
        job.job_id, entry.provider_artifact_id, entry.source.source_id
    )
    assert (
        hashlib.sha256(b"".join(retried.iter_chunks())).hexdigest()
        == entry.payload_checksum
    )


def test_openapi_binary_surface(client):
    schema = client.get("/openapi.json").json()
    endpoint = "/v1/jobs/{job_id}/artifacts/{provider_artifact_id}/payloads/{source_id}"
    operation = schema["paths"][endpoint]["get"]
    assert operation["operationId"] == "getPayloadContent"
    assert set(operation["responses"]["200"]["content"]) == {
        "audio/wav",
        "application/json",
    }
    assert {p["name"] for p in operation["parameters"]} == {
        "job_id",
        "provider_artifact_id",
        "source_id",
    }


@pytest.mark.parametrize(
    "case", ["duplicate-pair", "duplicate-source", "multiple-role"]
)
def test_duplicate_identity_and_source_role_reuse(provider, payload_request, case):
    job = provider.create_job(payload_request())
    raw = provider.get_result(job.job_id).model_dump()
    original = raw["payloads"][0]
    second = dict(original)
    if case == "duplicate-source":
        second["provider_artifact_id"] = "different-artifact"
    elif case == "multiple-role":
        second["role"] = "converted_vocal_candidate"
    raw["payloads"] = (original, second)
    with pytest.raises(ValidationError):
        PayloadArtifact.model_validate(raw)


def test_expired_source_http_mapping(client, provider, payload_request, monkeypatch):
    original = provider._with_payload

    def expired(artifact, capability):
        result, content = original(artifact, capability)
        entry = result.payloads[0].model_copy(
            update={"available_until": datetime.now(UTC) - timedelta(seconds=1)}
        )
        return result.model_copy(update={"payloads": (entry,)}), content

    monkeypatch.setattr(provider, "_with_payload", expired)
    job = provider.create_job(payload_request())
    result = provider.get_result(job.job_id)
    response = client.get(path(job.job_id, result.payloads[0]))
    assert response.status_code == 410
    assert response.json()["error"]["error_code"] == "PROVIDER_PAYLOAD_EXPIRED"
    assert response.json()["error"]["retryable"] is False
    assert provider.get_result(job.job_id) == result
    assert provider.get_job_status(job.job_id) == job


def test_acquisition_retry_over_http_after_partial_read(
    client, provider, payload_request
):
    job = provider.create_job(payload_request())
    result = provider.get_result(job.job_id)
    entry = result.payloads[0]
    content = provider.get_payload_content(
        job.job_id, entry.provider_artifact_id, entry.source.source_id
    )
    iterator = content.iter_chunks()
    assert 0 < len(next(iterator)) < entry.expected_size_bytes
    iterator.close()
    wire = client.get(path(job.job_id, entry))
    assert wire.status_code == 200
    assert hashlib.sha256(wire.content).hexdigest() == entry.payload_checksum
    assert provider.get_result(job.job_id) == result
    assert provider.get_job_status(job.job_id) == job


def test_payload_lineage_chain_keeps_root_and_parent(provider, payload_request):
    first_request = payload_request(JobType.VOCAL_CORRECTION)
    first = provider.get_result(provider.create_job(first_request).job_id)
    next_request = payload_request(JobType.VOCAL_CORRECTION)
    next_request = next_request.model_copy(
        update={
            "job_input": next_request.job_input.model_copy(
                update={
                    "source_asset_version_id": first.lineage.source_asset_version_id,
                    "parent_asset_version_id": first.output_asset_version_id,
                    "processing_chain_id": first.lineage.processing_chain_id,
                }
            )
        }
    )
    second = provider.get_result(provider.create_job(next_request).job_id)
    assert (
        second.lineage.source_asset_version_id == first.lineage.source_asset_version_id
    )
    assert second.lineage.parent_asset_version_id == first.output_asset_version_id
    assert second.lineage.processing_chain_id == first.lineage.processing_chain_id
    assert second.artifact_id != first.artifact_id
    assert second.payloads[0].source.source_id != first.payloads[0].source.source_id
    assert provider.get_result(first.run_id) == first
