"""Safe errors that may cross the Provider boundary."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class ErrorDetail(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    error_code: str
    message: str
    retryable: bool
    stage: str
    details_id: str


class VocalRuntimeError(Exception):
    status_code = 400

    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        retryable: bool = False,
        stage: str = "request_validation",
        details_id: str = "not-available",
    ) -> None:
        super().__init__(message)
        self.detail = ErrorDetail(
            error_code=error_code,
            message=message,
            retryable=retryable,
            stage=stage,
            details_id=details_id,
        )


class NotFoundError(VocalRuntimeError):
    status_code = 404


class ConflictError(VocalRuntimeError):
    status_code = 409


class InvalidStateTransitionError(ConflictError):
    pass


class UnsupportedCapabilityError(VocalRuntimeError):
    pass


class ContractVersionError(VocalRuntimeError):
    pass


def safe_validation_details(errors: list[dict[str, Any]]) -> str:
    """Return a stable identifier without echoing user payloads or local paths."""

    locations = [".".join(str(part) for part in item.get("loc", ())) for item in errors]
    return "validation:" + ",".join(sorted(locations))
