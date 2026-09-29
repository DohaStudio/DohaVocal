"""Transport-only response envelopes."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from dohavocal.domain.errors import ErrorDetail
from dohavocal.domain.jobs import JobType


class StrictResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProbeResponse(StrictResponse):
    status: Literal["ok", "ready"]
    provider_id: str


class CapabilitiesResponse(StrictResponse):
    provider_id: str
    api_contract_version: str
    capabilities: tuple[JobType, ...]
    supported_operations: tuple[str, ...]


class PayloadAcquisitionCapability(StrictResponse):
    supported: Literal[True] = True
    source_kinds: tuple[Literal["provider_subresource"], ...] = (
        "provider_subresource",
    )
    operation: Literal["GetPayloadContent"] = "GetPayloadContent"


class PayloadCapabilitiesResponse(CapabilitiesResponse):
    payload_acquisition: PayloadAcquisitionCapability


class ErrorResponse(StrictResponse):
    error: ErrorDetail
