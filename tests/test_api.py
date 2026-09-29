from copy import deepcopy

from dohavocal.config import DOHAVOCAL_PROVIDER_ID


def test_health_readiness_and_capabilities(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").json()["status"] == "ready"
    response = client.get("/v1/capabilities")

    assert response.status_code == 200
    assert response.json()["capabilities"] == [
        "vocal_generation",
        "voice_conversion",
        "vocal_correction",
        "vocal_analysis",
    ]


def test_canonical_provider_identity_is_stable_across_all_operations(
    client, generation_payload
):
    health = client.get("/health").json()
    readiness = client.get("/ready").json()
    capabilities = client.get("/v1/capabilities").json()

    created = client.post("/v1/jobs", json=generation_payload).json()
    status = client.get(f"/v1/jobs/{created['job_id']}").json()
    result = client.get(f"/v1/jobs/{created['job_id']}/result").json()
    manifest = client.get(
        f"/v1/model-manifests/{generation_payload['model_manifest_id']}"
    ).json()

    queued_payload = deepcopy(generation_payload)
    queued_payload["idempotency_key"] = "provider-identity-cancel-retry"
    queued_payload["settings_snapshot"] = {"fake_outcome": "queued"}
    queued = client.post("/v1/jobs", json=queued_payload).json()
    cancelled = client.post(f"/v1/jobs/{queued['job_id']}/cancel").json()
    retried = client.post(f"/v1/jobs/{queued['job_id']}/retry").json()

    assert health["provider_id"] == DOHAVOCAL_PROVIDER_ID
    assert readiness["provider_id"] == DOHAVOCAL_PROVIDER_ID
    assert capabilities["provider_id"] == DOHAVOCAL_PROVIDER_ID
    assert created["provider_id"] == DOHAVOCAL_PROVIDER_ID
    assert status["provider_id"] == DOHAVOCAL_PROVIDER_ID
    assert cancelled["provider_id"] == DOHAVOCAL_PROVIDER_ID
    assert retried["provider_id"] == DOHAVOCAL_PROVIDER_ID
    assert result["producer_id"] == DOHAVOCAL_PROVIDER_ID
    assert result["lineage"]["provider_id"] == DOHAVOCAL_PROVIDER_ID
    assert manifest["provider_id"] == DOHAVOCAL_PROVIDER_ID
    assert manifest["model_manifest_id"] == "dohavocal.fake-model@0.1.0"


def test_create_get_result_and_manifest(client, generation_payload):
    created = client.post("/v1/jobs", json=generation_payload)
    assert created.status_code == 201
    job = created.json()

    assert client.get(f"/v1/jobs/{job['job_id']}").json() == job
    result = client.get(f"/v1/jobs/{job['job_id']}/result")
    manifest = client.get(
        f"/v1/model-manifests/{generation_payload['model_manifest_id']}"
    )
    assert result.status_code == 200
    assert result.json()["lineage"]["job_id"] == job["job_id"]
    assert manifest.status_code == 200
    assert manifest.json()["license_status"] == "REVIEW_REQUIRED"


def test_cancel_and_retry(client, generation_payload):
    queued_payload = deepcopy(generation_payload)
    queued_payload["idempotency_key"] = "cancel-me"
    queued_payload["settings_snapshot"] = {"fake_outcome": "queued"}
    created = client.post("/v1/jobs", json=queued_payload).json()

    cancelled = client.post(f"/v1/jobs/{created['job_id']}/cancel")
    retried = client.post(f"/v1/jobs/{created['job_id']}/retry")

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert retried.status_code == 200
    assert retried.json()["retry_of_job_id"] == created["job_id"]


def test_not_found_conflict_and_validation_errors_are_structured(
    client, generation_payload
):
    missing = client.get("/v1/jobs/missing")
    invalid = deepcopy(generation_payload)
    invalid["capability"] = "unsupported"
    validation = client.post("/v1/jobs", json=invalid)

    first = client.post("/v1/jobs", json=generation_payload)
    conflict_payload = deepcopy(generation_payload)
    conflict_payload["settings_snapshot"] = {"temperature": 1}
    conflict = client.post("/v1/jobs", json=conflict_payload)

    assert missing.status_code == 404
    assert missing.json()["error"]["error_code"] == "JOB_NOT_FOUND"
    assert validation.status_code == 422
    assert validation.json()["error"]["error_code"] == "REQUEST_VALIDATION_FAILED"
    assert first.status_code == 201
    assert conflict.status_code == 409
    assert conflict.json()["error"]["error_code"] == "IDEMPOTENCY_CONFLICT"


def test_openapi_measurements_and_unique_operation_ids(client):
    schema = client.get("/openapi.json").json()
    methods = {"get", "post", "put", "patch", "delete"}
    operation_ids = [
        operation["operationId"]
        for path in schema["paths"].values()
        for method, operation in path.items()
        if method in methods
    ]

    assert len(schema["paths"]) == 10
    assert len(operation_ids) == 10
    assert len(operation_ids) == len(set(operation_ids))


def test_provider_contract_version_manifest_state_and_result_errors(
    client, generation_payload
):
    unknown_manifest = client.get("/v1/model-manifests/missing")
    queued_payload = deepcopy(generation_payload)
    queued_payload["idempotency_key"] = "result-before-success"
    queued_payload["settings_snapshot"] = {"fake_outcome": "queued"}
    queued = client.post("/v1/jobs", json=queued_payload).json()
    early_result = client.get(f"/v1/jobs/{queued['job_id']}/result")
    invalid_transition = client.post(f"/v1/jobs/{queued['job_id']}/retry")

    unsupported_provider = deepcopy(generation_payload)
    unsupported_provider["idempotency_key"] = "unsupported-provider"
    unsupported_provider["provider_id"] = "other"
    provider_error = client.post("/v1/jobs", json=unsupported_provider)

    unsupported_version = deepcopy(generation_payload)
    unsupported_version["idempotency_key"] = "unsupported-version"
    unsupported_version["api_contract_version"] = "9.0.0"
    version_error = client.post("/v1/jobs", json=unsupported_version)

    assert unknown_manifest.status_code == 404
    assert unknown_manifest.json()["error"]["error_code"] == "MODEL_MANIFEST_NOT_FOUND"
    assert early_result.status_code == 409
    assert early_result.json()["error"]["error_code"] == "JOB_RESULT_NOT_AVAILABLE"
    assert invalid_transition.status_code == 409
    assert invalid_transition.json()["error"]["error_code"] == "JOB_RETRY_NOT_ALLOWED"
    assert provider_error.status_code == 400
    assert provider_error.json()["error"]["error_code"] == "PROVIDER_NOT_SUPPORTED"
    assert version_error.status_code == 400
    assert version_error.json()["error"]["error_code"] == (
        "CONTRACT_VERSION_UNSUPPORTED"
    )
