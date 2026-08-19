import pytest

from dohavocal.domain.errors import ContractVersionError, UnsupportedCapabilityError
from dohavocal.domain.jobs import JobType


def test_capabilities_and_probes(provider):
    assert provider.get_capabilities() == tuple(JobType)
    assert provider.health() is True
    assert provider.readiness() is True


def test_contract_version_is_validated(provider, request_factory):
    request = request_factory().model_copy(update={"api_contract_version": "9.0.0"})

    with pytest.raises(ContractVersionError) as caught:
        provider.create_job(request)

    assert caught.value.detail.error_code == "CONTRACT_VERSION_UNSUPPORTED"


def test_provider_is_validated(provider, request_factory):
    request = request_factory().model_copy(update={"provider_id": "other"})

    with pytest.raises(UnsupportedCapabilityError) as caught:
        provider.create_job(request)

    assert caught.value.detail.error_code == "PROVIDER_NOT_SUPPORTED"


def test_published_manifest_cannot_be_mutated_through_a_returned_copy(provider):
    manifest_id = provider.settings.model_manifest_id
    detached = provider.get_model_manifest(manifest_id)
    detached.runtime_environment["gpu"] = "changed"

    assert provider.get_model_manifest(manifest_id).runtime_environment["gpu"] == (
        "not-used"
    )
    assert detached.artifact_checksum_scope == "fake_manifest_descriptor"
