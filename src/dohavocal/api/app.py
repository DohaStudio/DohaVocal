"""Runtime HTTP API composition root."""

from collections.abc import AsyncIterator

import anyio
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse

from dohavocal.application import VocalRuntimeService
from dohavocal.config import RuntimeSettings
from dohavocal.domain.errors import (
    ContractVersionError,
    ErrorDetail,
    VocalRuntimeError,
    safe_validation_details,
)
from dohavocal.domain.jobs import AnyVocalJob, CreateVocalJobRequest
from dohavocal.domain.manifests import ModelManifest
from dohavocal.domain.payloads import AnyVocalArtifact
from dohavocal.providers import FakeVocalProvider

from .models import (
    CapabilitiesResponse,
    ErrorResponse,
    PayloadAcquisitionCapability,
    PayloadCapabilitiesResponse,
    ProbeResponse,
)


def create_app(service: VocalRuntimeService | None = None) -> FastAPI:
    settings = RuntimeSettings()
    runtime_service = service or VocalRuntimeService(FakeVocalProvider(settings))
    app = FastAPI(
        title="DohaVocal Provider Runtime",
        version="0.2.0",
        description="Fake Provider 기반 Runtime Foundation",
    )
    app.state.runtime_service = runtime_service
    app.state.settings = settings

    @app.middleware("http")
    async def validate_payload_path(request: Request, call_next):
        path = request.scope["path"]
        if path.startswith("/v1/jobs/") and "/payloads/" in path:
            # Reject encoded path/credentials before routing decodes path segments.
            raw_path = request.scope.get("raw_path", b"")
            if (
                b"%" in raw_path
                or request.scope.get("query_string")
                or path.endswith("/")
            ):
                return JSONResponse(
                    status_code=400,
                    content=ErrorResponse(
                        error=ErrorDetail(
                            error_code="PROVIDER_PAYLOAD_INVALID_SOURCE_IDENTITY",
                            message="Payload 요청 식별자가 유효하지 않습니다.",
                            retryable=False,
                            stage="payload_acquisition",
                            details_id="not-available",
                        )
                    ).model_dump(mode="json"),
                )
        return await call_next(request)

    @app.exception_handler(VocalRuntimeError)
    async def runtime_error_handler(
        _request: Request, exc: VocalRuntimeError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(error=exc.detail).model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        detail = ErrorDetail(
            error_code="REQUEST_VALIDATION_FAILED",
            message="요청 형식이 유효하지 않습니다.",
            retryable=False,
            stage="request_validation",
            details_id=safe_validation_details(exc.errors()),
        )
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(error=detail).model_dump(mode="json"),
        )

    def current_service() -> VocalRuntimeService:
        return app.state.runtime_service

    @app.get(
        "/health",
        response_model=ProbeResponse,
        operation_id="getHealth",
    )
    def health() -> ProbeResponse:
        current_service().health()
        return ProbeResponse(status="ok", provider_id=settings.provider_id)

    @app.get(
        "/ready",
        response_model=ProbeResponse,
        operation_id="getReadiness",
    )
    def readiness() -> ProbeResponse:
        current_service().readiness()
        return ProbeResponse(status="ready", provider_id=settings.provider_id)

    @app.get(
        "/v1/capabilities",
        response_model=PayloadCapabilitiesResponse | CapabilitiesResponse,
        operation_id="getVocalCapabilities",
    )
    def capabilities(
        api_contract_version: str = "0.1.0",
    ) -> PayloadCapabilitiesResponse | CapabilitiesResponse:
        if api_contract_version not in current_service().supported_contract_versions():
            raise ContractVersionError(
                "CONTRACT_VERSION_UNSUPPORTED", "요청한 계약 버전을 지원하지 않습니다."
            )
        fields = dict(
            provider_id=settings.provider_id,
            api_contract_version=api_contract_version,
            capabilities=current_service().get_capabilities(),
            supported_operations=(
                "GetCapabilities",
                "CreateJob",
                "GetJobStatus",
                "CancelJob",
                "RetryJob",
                "GetResult",
                "GetModelManifest",
                "Health",
                "Readiness",
            ),
        )
        if api_contract_version == "0.2.0":
            fields["supported_operations"] += ("GetPayloadContent",)
            return PayloadCapabilitiesResponse(
                **fields, payload_acquisition=PayloadAcquisitionCapability()
            )
        return CapabilitiesResponse(**fields)

    @app.post(
        "/v1/jobs",
        response_model=AnyVocalJob,
        status_code=201,
        operation_id="createVocalJob",
        responses={400: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    )
    def create_job(request: CreateVocalJobRequest) -> AnyVocalJob:
        return current_service().create_job(request)

    @app.get(
        "/v1/jobs/{job_id}",
        response_model=AnyVocalJob,
        operation_id="getVocalJobStatus",
        responses={404: {"model": ErrorResponse}},
    )
    def get_job(job_id: str) -> AnyVocalJob:
        return current_service().get_job(job_id)

    @app.post(
        "/v1/jobs/{job_id}/cancel",
        response_model=AnyVocalJob,
        operation_id="cancelVocalJob",
        responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    )
    def cancel_job(job_id: str) -> AnyVocalJob:
        return current_service().cancel_job(job_id)

    @app.post(
        "/v1/jobs/{job_id}/retry",
        response_model=AnyVocalJob,
        operation_id="retryVocalJob",
        responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    )
    def retry_job(job_id: str) -> AnyVocalJob:
        return current_service().retry_job(job_id)

    @app.get(
        "/v1/jobs/{job_id}/result",
        response_model=AnyVocalArtifact,
        operation_id="getVocalJobResult",
        responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    )
    def get_result(job_id: str) -> AnyVocalArtifact:
        return current_service().get_result(job_id)

    @app.get(
        "/v1/jobs/{job_id}/artifacts/{provider_artifact_id}/payloads/{source_id}",
        response_class=StreamingResponse,
        operation_id="getPayloadContent",
        responses={
            200: {"content": {"audio/wav": {}, "application/json": {}}},
            400: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            410: {"model": ErrorResponse},
        },
    )
    def get_payload_content(
        job_id: str, provider_artifact_id: str, source_id: str, request: Request
    ) -> StreamingResponse:
        if "range" in request.headers:
            raise VocalRuntimeError(
                "PROVIDER_PAYLOAD_RANGE_UNSUPPORTED",
                "부분 Payload 요청을 지원하지 않습니다.",
                stage="payload_acquisition",
            )
        content = current_service().get_payload_content(
            job_id, provider_artifact_id, source_id
        )

        async def chunks() -> AsyncIterator[bytes]:
            for chunk in content.iter_chunks():
                await anyio.lowlevel.checkpoint()
                yield chunk

        return StreamingResponse(
            chunks(),
            media_type=content.media_type,
            headers={"Content-Length": str(len(content.content))},
        )

    @app.get(
        "/v1/model-manifests/{model_manifest_id}",
        response_model=ModelManifest,
        operation_id="getVocalModelManifest",
        responses={404: {"model": ErrorResponse}},
    )
    def get_model_manifest(model_manifest_id: str) -> ModelManifest:
        return current_service().get_model_manifest(model_manifest_id)

    return app


app = create_app()
