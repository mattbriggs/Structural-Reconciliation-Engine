"""Comparison job service — orchestrates the full localization pipeline.

Composes adaptation → reconciliation → interpretation → persistence → reporting
behind a single synchronous entry point (REQ-175). Each stage maps failures to
a lifecycle state with a stable machine code (SRS §3.20, §8.8): input/profile
problems ``REJECTED``; engine problems ``FAILED``; a renderer failure marks the
artifact failed but retains the (already persisted) result (REQ-173).

This service is synchronous; asynchronous execution wraps it via a job executor
(REQ-007).
"""

from __future__ import annotations

import uuid

from reconciliation.adapters.xml.errors import AdaptationError
from reconciliation.application.contracts.jobs import (
    ArtifactSummary,
    ComparisonRequest,
    ComparisonState,
    JobRecord,
    ReportFormat,
)
from reconciliation.application.contracts.localization import LocalizationValidationResult
from reconciliation.application.orchestration.registry import DocumentProfileRegistry
from reconciliation.application.ports.artifacts import ArtifactStore, ArtifactWriteError
from reconciliation.application.ports.results import ComparisonResultRepository, RepositoryError
from reconciliation.application.services.localization_validation import (
    LocalizationValidationService,
)
from reconciliation.core.contracts.commands import ExecutionContext, ReconcileTreesCommand
from reconciliation.core.engine import DefaultReconciliationEngine, ReconciliationEngine
from reconciliation.core.errors import ReconciliationError
from reconciliation.reporting.contracts import ReportOptions
from reconciliation.reporting.csv_renderer import CsvReportRenderer
from reconciliation.reporting.html.renderer import HtmlReportRenderer
from reconciliation.reporting.json_renderer import JsonReportRenderer
from reconciliation.reporting.rows import build_report_table


class JobOutcome:
    """The result of running a comparison job.

    :ivar record: The lifecycle record (state, summary, artifacts, errors).
    :ivar result: The localization result when completed, else ``None``.
    """

    __slots__ = ("record", "result")

    def __init__(
        self, record: JobRecord, result: LocalizationValidationResult | None
    ) -> None:
        self.record = record
        self.result = result


class ComparisonJobService:
    """Runs a localization comparison end to end.

    :param registry: Document profile registry (adapters + bundles).
    :param engine: Reconciliation engine (defaults to the pipeline engine).
    :param localization_service: Localization interpreter.
    :param result_repository: Optional result repository for persistence.
    :param artifact_store: Optional artifact store for generated reports.
    :param logger: Optional structlog logger; when provided, each run emits
        redaction-safe stage-timing and outcome events (REQ-243-246).
    """

    def __init__(
        self,
        registry: DocumentProfileRegistry,
        *,
        engine: ReconciliationEngine | None = None,
        localization_service: LocalizationValidationService | None = None,
        result_repository: ComparisonResultRepository | None = None,
        artifact_store: ArtifactStore | None = None,
        logger: object | None = None,
    ) -> None:
        self._registry = registry
        self._engine = engine or DefaultReconciliationEngine()
        self._localization = localization_service or LocalizationValidationService()
        self._results = result_repository
        self._artifacts = artifact_store
        self._logger = logger

    def run(self, request: ComparisonRequest) -> JobOutcome:
        """Execute a comparison job and return its outcome.

        Never raises for expected input/engine failures — those are captured in
        the returned :class:`JobRecord` with a stable code so a service can
        distinguish a technical failure from a completed comparison containing
        validation issues (REQ-246). When a logger is configured, a
        redaction-safe observability event is emitted.
        """
        outcome = self._run(request)
        if self._logger is not None:
            from reconciliation.application.services.observability import (
                build_observability_report,
            )
            from reconciliation.infrastructure.logging import emit_observability

            report = build_observability_report(outcome.record, outcome.result)
            emit_observability(self._logger, report)  # type: ignore[arg-type]
        return outcome

    def _run(self, request: ComparisonRequest) -> JobOutcome:
        job_id = request.job_id or f"job-{uuid.uuid4()}"
        correlation_id = f"corr-{job_id}"

        try:
            profile = self._registry.resolve(request.document_profile_id)
        except KeyError:
            return self._rejected(
                job_id, request, "UNSUPPORTED_CONTRACT",
                f"unknown document profile {request.document_profile_id!r}", correlation_id,
            )

        try:
            source_tree = profile.adapter.adapt_document(
                request.source_content, tree_id=f"{job_id}-source", document_uri="source"
            )
            locale_tree = profile.adapter.adapt_document(
                request.locale_content, tree_id=f"{job_id}-locale", document_uri="locale"
            )
        except AdaptationError as exc:
            return self._rejected(job_id, request, exc.code, exc.message, correlation_id)

        try:
            command = ReconcileTreesCommand(
                source_tree=source_tree,
                target_tree=locale_tree,
                normalization_profile=profile.bundle.normalization,
                matching_profile=profile.bundle.matching,
                alignment_profile=profile.bundle.alignment,
                operation_profile=profile.bundle.operation,
                suppression_profile=profile.bundle.suppression,
                execution_context=ExecutionContext(job_id=job_id, correlation_id=correlation_id),
            )
            reconciliation = self._engine.reconcile(command)
        except ReconciliationError as exc:
            return self._failed(job_id, request, exc.code, exc.message, correlation_id)

        result = self._localization.validate(
            reconciliation,
            source_tree,
            locale_tree,
            locale=request.locale,
            authoritative_side=request.authoritative_side,
            policy=request.policy,
        )

        if self._results is not None:
            try:
                self._results.save(result)
            except RepositoryError as exc:
                return self._failed(job_id, request, exc.code, exc.message, correlation_id)

        artifacts = self._render_artifacts(request, result, source_tree, locale_tree)

        return JobOutcome(
            record=JobRecord(
                job_id=job_id,
                state=ComparisonState.COMPLETED,
                locale=request.locale,
                status_counts=result.summary.status_counts,
                direct_issue_count=result.summary.direct_issue_count,
                artifacts=artifacts,
                correlation_id=correlation_id,
            ),
            result=result,
        )

    # -- Artifacts ---------------------------------------------------------

    def _render_artifacts(
        self,
        request: ComparisonRequest,
        result: LocalizationValidationResult,
        source_tree: object,
        locale_tree: object,
    ) -> tuple[ArtifactSummary, ...]:
        if not request.report_formats:
            return ()
        from reconciliation.core.contracts.tree import CanonicalTree

        assert isinstance(source_tree, CanonicalTree)
        assert isinstance(locale_tree, CanonicalTree)
        options = request.report_options or ReportOptions()
        table = build_report_table(
            result, source_tree=source_tree, locale_tree=locale_tree, options=options
        )
        artifacts: list[ArtifactSummary] = []
        for fmt in request.report_formats:
            name, media_type, content = self._render_one(
                fmt, result, table, source_tree, locale_tree
            )
            summary = ArtifactSummary(format=fmt, name=name, media_type=media_type)
            if self._artifacts is not None:
                try:
                    ref = self._artifacts.write(result.job_id, name, content, media_type)
                    summary = summary.model_copy(
                        update={"location": ref.location, "size_bytes": ref.size_bytes}
                    )
                except ArtifactWriteError:
                    # Renderer/store failure never invalidates the retained result.
                    summary = summary.model_copy(update={"size_bytes": 0})
            else:
                summary = summary.model_copy(
                    update={"size_bytes": len(content.encode("utf-8"))}
                )
            artifacts.append(summary)
        return tuple(artifacts)

    @staticmethod
    def _render_one(
        fmt: ReportFormat,
        result: LocalizationValidationResult,
        table: object,
        source_tree: object,
        locale_tree: object,
    ) -> tuple[str, str, str]:
        from reconciliation.core.contracts.tree import CanonicalTree
        from reconciliation.reporting.contracts import ReportTable

        assert isinstance(table, ReportTable)
        assert isinstance(source_tree, CanonicalTree)
        assert isinstance(locale_tree, CanonicalTree)
        if fmt is ReportFormat.CSV:
            return "report.csv", "text/csv", CsvReportRenderer().render(table)
        if fmt is ReportFormat.JSON:
            return (
                "result.json",
                "application/json",
                JsonReportRenderer().render_full(result, table),
            )
        return (
            "report.html",
            "text/html",
            HtmlReportRenderer().render(
                result, source_tree=source_tree, locale_tree=locale_tree
            ),
        )

    # -- Failure records ---------------------------------------------------

    @staticmethod
    def _rejected(
        job_id: str, request: ComparisonRequest, code: str, message: str, correlation_id: str
    ) -> JobOutcome:
        return JobOutcome(
            record=JobRecord(
                job_id=job_id,
                state=ComparisonState.REJECTED,
                locale=request.locale,
                error_code=code,
                error_message=message,
                correlation_id=correlation_id,
            ),
            result=None,
        )

    @staticmethod
    def _failed(
        job_id: str, request: ComparisonRequest, code: str, message: str, correlation_id: str
    ) -> JobOutcome:
        return JobOutcome(
            record=JobRecord(
                job_id=job_id,
                state=ComparisonState.FAILED,
                locale=request.locale,
                error_code=code,
                error_message=message,
                correlation_id=correlation_id,
            ),
            result=None,
        )
