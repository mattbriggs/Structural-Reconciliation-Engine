"""Comparison endpoints (REQ-178-182, SRS §4.4).

Creates and executes comparisons, reports lifecycle/summary, and serves results
with content negotiation (JSON or CSV) and the HTML report.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from reconciliation.application.contracts.jobs import ComparisonRequest, ComparisonState
from reconciliation.delivery.api.dependencies import ApiState
from reconciliation.delivery.api.dtos import CreateComparisonRequest, JobResponse
from reconciliation.delivery.api.error_handlers import error_response
from reconciliation.reporting.csv_renderer import CsvReportRenderer
from reconciliation.reporting.html.renderer import HtmlReportRenderer
from reconciliation.reporting.json_renderer import JsonReportRenderer
from reconciliation.reporting.rows import build_report_table

router = APIRouter(prefix="/api/v1/localization-comparisons", tags=["comparisons"])


def _state(request: Request) -> ApiState:
    return request.app.state.api  # type: ignore[no-any-return]


def _job_response(record: object) -> JobResponse:
    from reconciliation.application.contracts.jobs import JobRecord

    assert isinstance(record, JobRecord)
    return JobResponse(
        job_id=record.job_id,
        state=record.state,
        locale=record.locale,
        status_counts=record.status_counts,
        direct_issue_count=record.direct_issue_count,
        correlation_id=record.correlation_id,
    )


@router.post("", status_code=201)
def create_comparison(body: CreateComparisonRequest, request: Request) -> Response:
    """Create and execute a comparison (REQ-001, REQ-181)."""
    state = _state(request)
    outcome = state.service.run(
        ComparisonRequest(
            source_content=body.source_content,
            locale_content=body.locale_content,
            locale=body.locale,
            document_profile_id=body.document_profile_id,
            authoritative_side=body.authoritative_side,
        )
    )
    state.jobs[outcome.record.job_id] = outcome.record
    record = outcome.record
    if record.state is ComparisonState.REJECTED:
        return error_response(
            422, record.error_code or "COMPARISON_REJECTED",
            record.error_message or "rejected", correlation_id=record.correlation_id,
        )
    if record.state is ComparisonState.FAILED:
        return error_response(
            500, record.error_code or "COMPARISON_FAILED",
            record.error_message or "failed", correlation_id=record.correlation_id,
            retryable=True,
        )
    return _json_response(_job_response(record), status_code=201)


@router.get("/{job_id}")
def get_comparison(job_id: str, request: Request) -> Response:
    """Return a job's lifecycle state and summary."""
    record = _state(request).jobs.get(job_id)
    if record is None:
        return error_response(404, "NOT_FOUND", f"unknown job {job_id!r}")
    return _json_response(_job_response(record))


@router.get("/{job_id}/results")
def get_results(job_id: str, request: Request) -> Response:
    """Return JSON or CSV results by content negotiation (REQ-149, REQ-148)."""
    state = _state(request)
    result = state.result_repository.get(job_id)
    if result is None:
        return error_response(404, "NOT_FOUND", f"no results for job {job_id!r}")
    table = build_report_table(result)
    accept = request.headers.get("accept", "")
    if "text/csv" in accept:
        return Response(CsvReportRenderer().render(table), media_type="text/csv")
    return Response(
        JsonReportRenderer().render_full(result, table), media_type="application/json"
    )


@router.get("/{job_id}/report")
def get_report(job_id: str, request: Request) -> Response:
    """Return the self-contained HTML report (REQ-134)."""
    state = _state(request)
    result = state.result_repository.get(job_id)
    if result is None:
        return error_response(404, "NOT_FOUND", f"no report for job {job_id!r}")
    return Response(HtmlReportRenderer().render(result), media_type="text/html")


def _json_response(model: object, *, status_code: int = 200) -> Response:
    """Serialize a Pydantic response model to a JSON response."""
    from pydantic import BaseModel

    assert isinstance(model, BaseModel)
    return Response(
        model.model_dump_json(), media_type="application/json", status_code=status_code
    )
