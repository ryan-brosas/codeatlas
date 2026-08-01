from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from codeatlas_analysis.analysis_telemetry import InMemoryAnalysisTelemetry
from codeatlas_analysis.architecture_view import ArchitectureView
from codeatlas_analysis.change_impact import ChangeImpactReport
from codeatlas_analysis.cited_answers import CitedAnswer
from codeatlas_analysis.github_repository_source import (
    GitHubArchiveSource,
    UrlLibHttpTransport,
)
from codeatlas_analysis.repository_acquisition import (
    AcquisitionErrorCode,
    RepositoryAcquisitionError,
)
from codeatlas_analysis.repository_analysis import RepositoryAnalysis
from codeatlas_analysis.repository_intake import (
    InMemoryRepositoryIntake,
    RepositoryErrorCode,
    RepositoryStatus,
    RepositoryUrlError,
    normalize_public_github_repository,
)
from codeatlas_analysis.repository_snapshot_cache import (
    InMemoryRepositorySnapshotCache,
)


class HealthResponse(BaseModel):
    service: Literal["codeatlas-analysis"]
    status: Literal["ok"]


class RepositoryIntakeRequest(BaseModel):
    repository_url: str


class RepositoryQuestionRequest(BaseModel):
    repository_url: str
    question: str


class RepositoryIdentityResponse(BaseModel):
    id: str
    host: Literal["github.com"]
    owner: str
    name: str
    canonical_url: str


class RepositoryIntakeResponse(BaseModel):
    repository: RepositoryIdentityResponse
    status: RepositoryStatus


class ApiErrorDetail(BaseModel):
    code: RepositoryErrorCode | AcquisitionErrorCode | Literal["invalid_request"]
    message: str
    field: str


class ApiErrorResponse(BaseModel):
    error: ApiErrorDetail


_repository_intake = InMemoryRepositoryIntake()
_analysis_telemetry = InMemoryAnalysisTelemetry()
_repository_snapshot_cache = InMemoryRepositorySnapshotCache(
    max_entries=32,
    max_source_bytes=16 * 1024 * 1024,
    ttl_seconds=300.0,
    observer=_analysis_telemetry,
)
_repository_analysis = RepositoryAnalysis(
    GitHubArchiveSource(
        UrlLibHttpTransport(),
        cache=_repository_snapshot_cache,
        observer=_analysis_telemetry,
    ),
    observer=_analysis_telemetry,
)
app = FastAPI(
    title="CodeAtlas Analysis API",
    version="0.1.0",
)


def api_error_response(
    *,
    status_code: int,
    code: RepositoryErrorCode | AcquisitionErrorCode | Literal["invalid_request"],
    message: str,
    field: str,
) -> JSONResponse:
    response = ApiErrorResponse(error=ApiErrorDetail(code=code, message=message, field=field))
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(mode="json"),
    )


def repository_error(error: RepositoryUrlError) -> JSONResponse:
    return api_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        code=error.code,
        message=error.message,
        field="repository_url",
    )


def repository_acquisition_error(error: RepositoryAcquisitionError) -> JSONResponse:
    status_code = (
        status.HTTP_413_CONTENT_TOO_LARGE
        if error.code is AcquisitionErrorCode.ARCHIVE_LIMIT_EXCEEDED
        else status.HTTP_502_BAD_GATEWAY
    )
    return api_error_response(
        status_code=status_code,
        code=error.code,
        message=error.message,
        field="repository_url",
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error(
    _request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    field = "request"
    errors = error.errors()
    if errors:
        location = errors[0].get("loc", ())
        if location and isinstance(location[-1], str):
            field = location[-1]
    return api_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="invalid_request",
        message="Request validation failed.",
        field=field,
    )


@app.get(
    "/v1/health",
    operation_id="get_health",
    response_model=HealthResponse,
    tags=["system"],
)
def get_health() -> HealthResponse:
    return HealthResponse(service="codeatlas-analysis", status="ok")


@app.post(
    "/v1/repositories",
    operation_id="submit_repository",
    response_model=RepositoryIntakeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ApiErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ApiErrorResponse},
    },
    tags=["repositories"],
)
def submit_repository(
    request: RepositoryIntakeRequest,
) -> RepositoryIntakeResponse | JSONResponse:
    try:
        record = _repository_intake.submit(request.repository_url)
    except RepositoryUrlError as error:
        return repository_error(error)

    return RepositoryIntakeResponse(
        repository=RepositoryIdentityResponse(
            id=record.repository.id,
            host="github.com",
            owner=record.repository.owner,
            name=record.repository.name,
            canonical_url=record.repository.canonical_url,
        ),
        status=record.status,
    )


def get_repository_analysis() -> RepositoryAnalysis:
    return _repository_analysis


@app.post(
    "/v1/architecture",
    operation_id="analyze_repository_architecture",
    response_model=ArchitectureView,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ApiErrorResponse},
        status.HTTP_413_CONTENT_TOO_LARGE: {"model": ApiErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ApiErrorResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": ApiErrorResponse},
    },
    tags=["analysis"],
)
def analyze_repository_architecture(
    request: RepositoryIntakeRequest,
    analysis: Annotated[RepositoryAnalysis, Depends(get_repository_analysis)],
) -> ArchitectureView | JSONResponse:
    try:
        repository = normalize_public_github_repository(request.repository_url)
    except RepositoryUrlError as error:
        return repository_error(error)
    try:
        return analysis.analyze(repository)
    except RepositoryAcquisitionError as error:
        return repository_acquisition_error(error)


@app.post(
    "/v1/questions",
    operation_id="answer_repository_question",
    response_model=CitedAnswer,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ApiErrorResponse},
        status.HTTP_413_CONTENT_TOO_LARGE: {"model": ApiErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ApiErrorResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": ApiErrorResponse},
    },
    tags=["analysis"],
)
def answer_repository_question(
    request: RepositoryQuestionRequest,
    analysis: Annotated[RepositoryAnalysis, Depends(get_repository_analysis)],
) -> CitedAnswer | JSONResponse:
    try:
        repository = normalize_public_github_repository(request.repository_url)
    except RepositoryUrlError as error:
        return repository_error(error)
    try:
        return analysis.answer(repository, request.question)
    except RepositoryAcquisitionError as error:
        return repository_acquisition_error(error)


@app.post(
    "/v1/impact",
    operation_id="analyze_repository_change_impact",
    response_model=ChangeImpactReport,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ApiErrorResponse},
        status.HTTP_413_CONTENT_TOO_LARGE: {"model": ApiErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ApiErrorResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": ApiErrorResponse},
    },
    tags=["analysis"],
)
def analyze_repository_change_impact(
    request: RepositoryQuestionRequest,
    analysis: Annotated[RepositoryAnalysis, Depends(get_repository_analysis)],
) -> ChangeImpactReport | JSONResponse:
    try:
        repository = normalize_public_github_repository(request.repository_url)
    except RepositoryUrlError as error:
        return repository_error(error)
    try:
        return analysis.impact(repository, request.question)
    except RepositoryAcquisitionError as error:
        return repository_acquisition_error(error)
