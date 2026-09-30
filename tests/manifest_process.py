"""Fresh process Manifest probe using the real API composition root."""

import base64
import json
import os
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

from dohavocal.api.app import create_app
from dohavocal.config import RuntimeSettings


def main():
    started = time.time_ns()
    data = json.load(sys.stdin)
    settings = RuntimeSettings(
        runtime_mode=data["mode"],
        database_path=Path(data["database"]) if data["mode"] == "sqlite" else None,
        initialize_database=data["mode"] == "sqlite" and data["stage"] == "a",
    )
    observations = {}
    with TestClient(create_app(settings=settings)) as client:
        for version in ("0.1.0", "0.2.0"):
            manifest_id = "dohavocal.fake-model@" + version
            response = client.get("/v1/model-manifests/" + manifest_id)
            assert response.status_code == 200
            record = {"manifest": response.json()}
            if data["mode"] == "sqlite":
                request = dict(
                    data["request"],
                    api_contract_version=version,
                    model_manifest_id=manifest_id,
                    idempotency_key=version,
                )
                if data["stage"] == "a":
                    job_response = client.post("/v1/jobs", json=request)
                    assert job_response.status_code == 201
                else:
                    job_response = client.get("/v1/jobs/" + data["jobs"][version])
                    assert job_response.status_code == 200
                job = job_response.json()
                result_response = client.get("/v1/jobs/" + job["job_id"] + "/result")
                assert result_response.status_code == 200
                result = result_response.json()
                assert (
                    result["lineage"]["model_manifest_id"]
                    == job["model_manifest_id"]
                    == manifest_id
                )
                replay = client.post("/v1/jobs", json=request)
                assert replay.status_code == 201 and replay.json() == job
                content = None
                if version == "0.2.0":
                    entry = result["payloads"][0]
                    payload = client.get(
                        "/v1/jobs/"
                        + job["job_id"]
                        + "/artifacts/"
                        + result["artifact_id"]
                        + "/payloads/"
                        + entry["source"]["source_id"]
                    )
                    assert payload.status_code == 200
                    content = base64.b64encode(payload.content).decode()
                record.update(job=job, result=result, content=content)
            observations[version] = record
    print(
        json.dumps(
            {
                "pid": os.getpid(),
                "started_ns": started,
                "finished_ns": time.time_ns(),
                "observations": observations,
            }
        )
    )


if __name__ == "__main__":
    main()
