"""Runtime HTTP API composition root."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from dohavocal.application import VocalRuntimeService
from dohavocal.config import RuntimeSettings
from dohavocal.domain.artifacts import VocalArtifact
from dohavocal.domain.errors import (
    ErrorDetail,
    VocalRuntimeError,
    safe_validation_details,
)
from dohavocal.domain.jobs import AnyVocalJob, CreateVocalJobRequest
from dohavocal.domain.manifests import ModelManifest
from dohavocal.providers import FakeVocalProvider

from .models import CapabilitiesResponse, ErrorResponse, ProbeResponse


def create_app(service: VocalRuntimeService | None = None) -> FastAPI:
    settings = RuntimeSettings()
    runtime_service = service or VocalRuntimeService(FakeVocalProvider(settings))
    app = FastAPI(
        title="DohaVocal Provider Runtime",
        version="0.1.0",
        description="Fake Provider 기반 Runtime Foundation",
    )
    app.state.runtime_service = runtime_service
    app.state.settings = settings

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
        response_model=CapabilitiesResponse,
        operation_id="getVocalCapabilities",
    )
    def capabilities() -> CapabilitiesResponse:
        return CapabilitiesResponse(
            provider_id=settings.provider_id,
            api_contract_version=settings.api_contract_version,
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
        response_model=VocalArtifact,
        operation_id="getVocalJobResult",
        responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    )
    def get_result(job_id: str) -> VocalArtifact:
        return current_service().get_result(job_id)

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
