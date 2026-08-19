from copy import deepcopy

import pytest
from pydantic import ValidationError

from dohavocal.domain.jobs import CreateVocalJobRequest


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("token", "sensitive-value"),
        ("api_key", "sensitive-value"),
        ("model_path", "C:\\private\\model.bin"),
        ("dataset_path", "/private/dataset"),
        ("path", "C:\\Users\\person\\voice.wav"),
        ("value", "../private/voice.wav"),
        ("value", "file:///private/voice.wav"),
        ("value", "\\\\server\\share\\voice.wav"),
    ],
)
def test_sensitive_settings_are_rejected_without_echo(
    client, generation_payload, key, value
):
    payload = deepcopy(generation_payload)
    payload["settings_snapshot"] = {key: value}

    response = client.post("/v1/jobs", json=payload)

    assert response.status_code == 422
    body = response.text
    assert value not in body
    assert "Traceback" not in body
    assert "stack trace" not in body.lower()


def test_local_absolute_path_is_rejected_in_nested_settings(generation_payload):
    payload = deepcopy(generation_payload)
    payload["settings_snapshot"] = {"nested": {"value": "D:\\models\\x"}}

    with pytest.raises(ValidationError):
        CreateVocalJobRequest.model_validate(payload)


def test_absolute_path_cannot_be_disguised_as_an_artifact_id(
    client, generation_payload
):
    payload = deepcopy(generation_payload)
    payload["input_artifact_ids"] = ["C:\\private\\voice.wav"]

    response = client.post("/v1/jobs", json=payload)

    assert response.status_code == 422
    assert "C:\\private\\voice.wav" not in response.text


@pytest.mark.parametrize(
    "value",
    ["artifact://vocal/item-1", "https://example.invalid/schema", "tokenizer-v1"],
)
def test_logical_references_are_not_rejected_as_paths(generation_payload, value):
    payload = deepcopy(generation_payload)
    payload["settings_snapshot"] = {"reference": value, "tokenizer": "local"}

    request = CreateVocalJobRequest.model_validate(payload)

    assert request.settings_snapshot["reference"] == value
