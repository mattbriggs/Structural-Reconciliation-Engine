"""Tests for the comparison job orchestration (failure branches + artifacts)."""

from __future__ import annotations

import pytest

from reconciliation.application.contracts.jobs import (
    ComparisonRequest,
    ComparisonState,
    ReportFormat,
)
from reconciliation.application.orchestration.comparison_job import ComparisonJobService
from reconciliation.core.contracts.commands import ReconcileTreesCommand
from reconciliation.core.errors import MatchingError
from reconciliation.delivery.composition import build_default_registry
from reconciliation.infrastructure.artifact_store import FilesystemArtifactStore
from reconciliation.infrastructure.persistence.database import Database
from reconciliation.infrastructure.persistence.result_repository import (
    SqliteComparisonResultRepository,
)

SRC = '<map><topicref keys="intro" href="i.dita"/><topicref keys="gone" href="g.dita"/></map>'
LOC = '<map><topicref keys="intro" href="i.dita"/></map>'


def _request(**overrides) -> ComparisonRequest:
    base = dict(
        source_content=SRC,
        locale_content=LOC,
        locale="fr-FR",
        document_profile_id="dita-map-v1",
        job_id="job-orch",
    )
    base.update(overrides)
    return ComparisonRequest(**base)


def test_unknown_profile_is_rejected() -> None:
    service = ComparisonJobService(build_default_registry())
    outcome = service.run(_request(document_profile_id="nope"))
    assert outcome.record.state is ComparisonState.REJECTED
    assert outcome.record.error_code == "UNSUPPORTED_CONTRACT"
    assert outcome.result is None


def test_malformed_input_is_rejected() -> None:
    service = ComparisonJobService(build_default_registry())
    outcome = service.run(_request(source_content="<map><bad></map>"))
    assert outcome.record.state is ComparisonState.REJECTED
    assert outcome.record.error_code == "INVALID_INPUT"


def test_engine_failure_marks_job_failed() -> None:
    class _FailingEngine:
        def reconcile(self, command: ReconcileTreesCommand):
            raise MatchingError("boom")

    service = ComparisonJobService(build_default_registry(), engine=_FailingEngine())
    outcome = service.run(_request())
    assert outcome.record.state is ComparisonState.FAILED
    assert outcome.record.error_code == "MATCHING_FAILED"


def test_artifacts_written_to_store(tmp_path) -> None:
    db = Database()
    db.create_all()
    store = FilesystemArtifactStore(tmp_path)
    service = ComparisonJobService(
        build_default_registry(),
        result_repository=SqliteComparisonResultRepository(db.session_factory),
        artifact_store=store,
    )
    outcome = service.run(
        _request(report_formats=(ReportFormat.CSV, ReportFormat.JSON, ReportFormat.HTML))
    )
    db.dispose()
    assert outcome.record.state is ComparisonState.COMPLETED
    formats = {a.format for a in outcome.record.artifacts}
    assert formats == {ReportFormat.CSV, ReportFormat.JSON, ReportFormat.HTML}
    assert all(a.location and a.size_bytes > 0 for a in outcome.record.artifacts)


def test_artifacts_sized_without_store() -> None:
    service = ComparisonJobService(build_default_registry())
    outcome = service.run(_request(report_formats=(ReportFormat.CSV,)))
    assert outcome.record.artifacts[0].size_bytes > 0
    assert outcome.record.artifacts[0].location is None


def test_policy_locale_mismatch_rejected_at_contract() -> None:
    from pydantic import ValidationError

    from reconciliation.application.contracts.policy import LocaleVariationPolicy

    with pytest.raises(ValidationError):
        _request(
            policy=LocaleVariationPolicy(policy_id="p", version="v1", locale="de-DE")
        )
