"""Tests for job executors (REQ-007): async boundary lives outside the core."""

from __future__ import annotations

from reconciliation.application.contracts.jobs import ComparisonRequest, ComparisonState
from reconciliation.application.orchestration.comparison_job import ComparisonJobService
from reconciliation.delivery.composition import build_default_registry
from reconciliation.infrastructure.jobs.executor import SynchronousJobExecutor
from reconciliation.infrastructure.jobs.in_memory import ThreadedJobExecutor

SRC = '<map><topicref keys="intro" href="i.dita"/><topicref keys="gone" href="g.dita"/></map>'
LOC = '<map><topicref keys="intro" href="i.dita"/></map>'


def _request(job_id: str) -> ComparisonRequest:
    return ComparisonRequest(
        source_content=SRC,
        locale_content=LOC,
        locale="fr-FR",
        document_profile_id="dita-map-v1",
        job_id=job_id,
    )


def _service() -> ComparisonJobService:
    return ComparisonJobService(build_default_registry())


def test_synchronous_executor_completes_on_submit() -> None:
    executor = SynchronousJobExecutor(_service())
    record = executor.submit(_request("sync-1"))
    assert record.state is ComparisonState.COMPLETED
    assert executor.get("sync-1").state is ComparisonState.COMPLETED
    assert executor.get("missing") is None


def test_threaded_executor_returns_running_then_completes() -> None:
    executor = ThreadedJobExecutor(_service())
    try:
        record = executor.submit(_request("async-1"))
        # The submit call returns before the work finishes (async boundary).
        assert record.state is ComparisonState.RUNNING
        final = executor.wait("async-1", timeout=10)
        assert final is not None
        assert final.state is ComparisonState.COMPLETED
        assert final.status_counts  # summary populated
    finally:
        executor.shutdown()


def test_threaded_executor_generates_job_id_when_absent() -> None:
    executor = ThreadedJobExecutor(_service())
    try:
        record = executor.submit(
            ComparisonRequest(
                source_content=SRC, locale_content=LOC, locale="fr-FR",
                document_profile_id="dita-map-v1",
            )
        )
        assert record.job_id.startswith("job-")
        assert executor.wait(record.job_id, timeout=10).state is ComparisonState.COMPLETED
    finally:
        executor.shutdown()
