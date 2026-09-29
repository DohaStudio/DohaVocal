"""Versioned payload descriptors and HTTP-independent binary content."""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from pydantic import Field, field_validator, model_validator

from dohavocal.domain.artifacts import VocalArtifact
from dohavocal.domain.jobs import FrozenModel, JobType

PRIMARY_ROLES = {
    JobType.VOCAL_GENERATION: "generated_vocal_candidate",
    JobType.VOICE_CONVERSION: "converted_vocal_candidate",
    JobType.VOCAL_CORRECTION: "corrected_vocal_candidate",
    JobType.VOCAL_ANALYSIS: "vocal_analysis_result",
}
PayloadRole = Literal[
    "generated_vocal_candidate",
    "converted_vocal_candidate",
    "corrected_vocal_candidate",
    "vocal_analysis_result",
]


def is_opaque_id(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}", value)) and (
        ".." not in value
    )


class PayloadSource(FrozenModel):
    kind: Literal["provider_subresource"] = "provider_subresource"
    source_id: str = Field(
        min_length=1, max_length=200, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
    )

    @field_validator("source_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not is_opaque_id(value):
            raise ValueError("Source identity must be an opaque identifier.")
        return value


class PayloadEntry(FrozenModel):
    provider_artifact_id: str = Field(
        min_length=1, max_length=200, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
    )
    role: PayloadRole
    source: PayloadSource
    checksum_algorithm: Literal["sha256"] = "sha256"
    payload_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_size_bytes: int = Field(gt=0)
    expected_media_type: Literal["audio/wav", "audio/flac", "application/json"]
    available_until: datetime | None

    @field_validator("provider_artifact_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not is_opaque_id(value):
            raise ValueError("Artifact identity must be an opaque identifier.")
        return value

    @field_validator("available_until")
    @classmethod
    def validate_expiry(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() != timedelta(0):
            raise ValueError("Availability must be timezone-aware UTC.")
        return value

    @model_validator(mode="after")
    def validate_media(self) -> "PayloadEntry":
        analysis = self.role == "vocal_analysis_result"
        if analysis != (self.expected_media_type == "application/json"):
            raise ValueError("Payload role and media type disagree.")
        return self


class MetadataPayloadArtifact(VocalArtifact):
    """Explicit 0.2.0 metadata-only variant, never sent for a 0.1.0 Job."""

    payload_present: Literal[False] = False
    payloads: tuple[PayloadEntry, ...] = Field(max_length=0)


class PayloadArtifact(VocalArtifact):
    payload_present: Literal[True] = True
    payloads: tuple[PayloadEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_bindings(self) -> "PayloadArtifact":
        # No auxiliary roles exist in this contract version.
        if len(self.payloads) != 1:
            raise ValueError("Exactly one primary payload is required.")
        entry = self.payloads[0]
        if (
            entry.provider_artifact_id != self.artifact_id
            or self.run_id != self.lineage.job_id
            or self.producer_id != self.lineage.provider_id
            or (self.artifact_kind == "analysis")
            != (entry.role == "vocal_analysis_result")
            or self.media_type != entry.expected_media_type
            or self.size_bytes != entry.expected_size_bytes
        ):
            raise ValueError("Payload and enclosing Result bindings disagree.")
        return self


AnyVocalArtifact = PayloadArtifact | MetadataPayloadArtifact | VocalArtifact
SourceScope = tuple[str, str, str, str, str]


def source_scope(result: PayloadArtifact) -> SourceScope:
    entry = result.payloads[0]
    return (
        result.producer_id,
        result.run_id,
        entry.provider_artifact_id,
        entry.role,
        entry.source.source_id,
    )


@dataclass(frozen=True, slots=True)
class PayloadContent:
    """Immutable process-local bytes; each transfer owns a fresh iterator."""

    content: bytes
    media_type: str

    def iter_chunks(self) -> Iterator[bytes]:
        for offset in range(0, len(self.content), 512):
            yield self.content[offset : offset + 512]
