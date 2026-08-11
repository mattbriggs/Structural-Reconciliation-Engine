"""Structured API error handling (REQ-179, REQ-180).

All API errors carry a stable code, message, correlation id, retryability, and
an optional field/location so clients can react programmatically.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from reconciliation.application.errors import ApplicationError
from reconciliation.application.ports.results import RepositoryError

_HTTP_BY_CODE: dict[str, int] = {
    "COMPARISON_REJECTED": 422,
    "INVALID_POLICY": 422,
    "RECOMMENDATION_ERROR": 500,
    "REPOSITORY_ERROR": 500,
}


def error_response(
    status_code: int,
    code: str,
    message: str,
    *,
    correlation_id: str | None = None,
    retryable: bool = False,
    field: str | None = None,
) -> JSONResponse:
    """Build a structured JSON error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "correlation_id": correlation_id,
            "retryable": retryable,
            "field": field,
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register exception handlers producing structured error bodies."""

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(p) for p in first.get("loc", []) if p != "body") or None
        return error_response(
            422, "INVALID_INPUT", "request body failed validation", field=field
        )

    @app.exception_handler(ApplicationError)
    async def _application(request: Request, exc: ApplicationError) -> JSONResponse:
        return error_response(
            _HTTP_BY_CODE.get(exc.code, 400), exc.code, exc.message,
            retryable=exc.retryable,
        )

    @app.exception_handler(RepositoryError)
    async def _repository(request: Request, exc: RepositoryError) -> JSONResponse:
        return error_response(500, "REPOSITORY_ERROR", exc.message, retryable=True)
