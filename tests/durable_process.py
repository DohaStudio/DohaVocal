"""Independent process harness; synthetic request only, no network or user data."""

import base64
import json
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from dohavocal.api.app import create_app
from dohavocal.config import RuntimeSettings
from dohavocal.providers.fake import FakeVocalProvider


def main():
    data = json.load(sys.stdin)
    mode = data["mode"]
    if mode == "reopen":

        def forbidden(*args, **kwargs):
            raise AssertionError("replay must never generate payload")

        FakeVocalProvider._with_payload = staticmethod(forbidden)
        FakeVocalProvider._build_artifact = forbidden
    settings = RuntimeSettings(
        runtime_mode="sqlite",
        database_path=Path(data["database"]),
        initialize_database=False,
    )
    with TestClient(create_app(settings=settings)) as client:
        request = data["request"]
        if mode == "reopen":
            job = client.get("/v1/jobs/" + data["job_id"])
        else:
            job = client.post("/v1/jobs", json=request)
        assert job.status_code in (200, 201), job.text
        job = job.json()
        result_response = client.get("/v1/jobs/" + job["job_id"] + "/result")
        assert result_response.status_code == 200, result_response.text
        result = result_response.json()
        content = None
        if result["payload_present"]:
            entry = result["payloads"][0]
            response = client.get(
                "/v1/jobs/"
                + job["job_id"]
                + "/artifacts/"
                + result["artifact_id"]
                + "/payloads/"
                + entry["source"]["source_id"]
            )
            assert response.status_code == 200, response.text
            content = base64.b64encode(response.content).decode()
        replay = client.post("/v1/jobs", json=request)
        assert replay.status_code == 201 and replay.json() == job
        conflict = dict(request, settings_snapshot={"different": True})
        assert client.post("/v1/jobs", json=conflict).status_code == 409
        output = {"job": job, "result": result, "bytes": content}
        print(json.dumps(output), flush=True)
        if mode == "abrupt":
            os._exit(0)
    # Graceful context has shut down all owned resources before process exit.


if __name__ == "__main__":
    main()
