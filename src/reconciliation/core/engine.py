"""Reconciliation engine: the pure, synchronous core boundary (REQ-171-174).

Coordinates the domain-neutral pipeline in its required deterministic order::

    normalize -> evidence -> match -> align -> classify -> root-cause -> suppress

The engine consumes a :class:`ReconcileTreesCommand` and returns a
:class:`ReconciliationResult`. It references no locale, DITA, CCMS, HTML, CSV,
or pricing concept (REQ-171) and performs no I/O. Application-level asynchrony
must wrap this method rather than modifying core semantics (REQ-007).
"""

from __future__ import annotations

import time
from typing import Protocol

from reconciliation.core.alignment.aligner import TreeAlignerService
from reconciliation.core.causality.analyzer import RootCauseAnalyzerService
from reconciliation.core.classification.classifier import StructuralOperationClassifierService
from reconciliation.core.contracts.commands import ReconcileTreesCommand
from reconciliation.core.contracts.diagnostics import (
    EngineDiagnostic,
    PipelineStage,
    Severity,
)
from reconciliation.core.contracts.results import ProfileVersions, ReconciliationResult
from reconciliation.core.errors import ResourceLimitExceededError
from reconciliation.core.evidence.extractor import IdentityEvidenceExtractorService
from reconciliation.core.matching.matcher import NodeMatcherService
from reconciliation.core.metrics.calculator import StageTimer, check_pre_limits
from reconciliation.core.normalization.service import TreeNormalizerService
from reconciliation.core.suppression.service import CascadeSuppressionService
from reconciliation.core.validation.profile_validator import validate_profiles
from reconciliation.core.validation.tree_validator import validate_tree
from reconciliation.version import CORE_CONTRACT_VERSION, ENGINE_VERSION


class ReconciliationEngine(Protocol):
    """Structural contract for the core reconciliation boundary (REQ-171)."""

    def reconcile(self, command: ReconcileTreesCommand) -> ReconciliationResult:
        """Reconcile two canonical trees and return a domain-neutral result."""
        ...


class DefaultReconciliationEngine:
    """Default pipeline engine wiring the stage services via constructor injection.

    Every stage service is injectable so tests and extensions can substitute a
    strategy through its port without subclassing the engine (REQ-227). The
    defaults form a complete, deterministic initial-release pipeline.
    """

    def __init__(
        self,
        *,
        normalizer: TreeNormalizerService | None = None,
        extractor: IdentityEvidenceExtractorService | None = None,
        matcher: NodeMatcherService | None = None,
        aligner: TreeAlignerService | None = None,
        classifier: StructuralOperationClassifierService | None = None,
        analyzer: RootCauseAnalyzerService | None = None,
        suppressor: CascadeSuppressionService | None = None,
    ) -> None:
        self._normalizer = normalizer or TreeNormalizerService()
        self._extractor = extractor or IdentityEvidenceExtractorService()
        self._matcher = matcher or NodeMatcherService()
        self._aligner = aligner or TreeAlignerService()
        self._classifier = classifier or StructuralOperationClassifierService()
        self._analyzer = analyzer or RootCauseAnalyzerService()
        self._suppressor = suppressor or CascadeSuppressionService()

    def reconcile(self, command: ReconcileTreesCommand) -> ReconciliationResult:
        """Run the full reconciliation pipeline.

        :param command: Validated trees, profiles, and execution context.
        :returns: An immutable :class:`ReconciliationResult`.
        :raises InvalidTreeError: If either tree violates its invariants.
        :raises InvalidProfileError: If the supplied profiles conflict.
        :raises ResourceLimitExceededError: If a limit is exceeded and the
            execution context did not request an incomplete result instead.
        """
        ctx = command.execution_context
        correlation_id = ctx.correlation_id

        # Fail-fast validation at the boundary (REQ-005, REQ-174).
        validate_tree(command.source_tree, correlation_id=correlation_id)
        validate_tree(command.target_tree, correlation_id=correlation_id)
        validate_profiles(
            command.matching_profile,
            command.operation_profile,
            command.suppression_profile,
        ).raise_if_invalid(correlation_id=correlation_id)

        diagnostics: list[EngineDiagnostic] = []
        complete = True
        timer = StageTimer(len(command.source_tree.nodes), len(command.target_tree.nodes))

        try:
            check_pre_limits(
                command.source_tree,
                command.target_tree,
                ctx.resource_limits,
                correlation_id=correlation_id,
            )
        except ResourceLimitExceededError as exc:
            if not ctx.incomplete_on_limit:
                raise
            complete = False
            diagnostics.append(
                EngineDiagnostic(
                    code=exc.code,
                    severity=Severity.ERROR,
                    stage=PipelineStage.NORMALIZATION,
                    message=exc.message,
                    metadata={k: v for k, v in exc.context.items() if isinstance(v, int | str)},
                )
            )
            return self._incomplete_result(command, diagnostics, timer)

        # Normalization (REQ-016-024).
        start = time.perf_counter()
        norm_source = self._normalizer.normalize(
            command.source_tree, command.normalization_profile
        )
        norm_target = self._normalizer.normalize(
            command.target_tree, command.normalization_profile
        )
        timer.record(PipelineStage.NORMALIZATION, start, result_count=2)

        # Evidence extraction (REQ-025-036).
        start = time.perf_counter()
        evidence = self._extractor.extract(
            norm_source.tree, norm_target.tree, command.matching_profile
        )
        timer.record(
            PipelineStage.EVIDENCE, start,
            result_count=len(evidence.source) + len(evidence.target),
        )
        diagnostics.extend(self._duplicate_id_diagnostics(evidence))

        # Matching (REQ-037-051).
        start = time.perf_counter()
        graph = self._matcher.match(evidence, command.matching_profile)
        timer.record(
            PipelineStage.MATCHING, start,
            candidate_count=len(graph.candidates),
            result_count=len(graph.confirmed),
        )

        # Alignment (REQ-052-060).
        start = time.perf_counter()
        alignment = self._aligner.align(
            norm_source.tree, norm_target.tree, graph, command.alignment_profile
        )
        timer.record(
            PipelineStage.ALIGNMENT, start, result_count=len(alignment.regions)
        )

        # Classification (REQ-061-072).
        start = time.perf_counter()
        operations = self._classifier.classify(
            norm_source.tree, norm_target.tree, graph, alignment, command.operation_profile
        )
        timer.record(
            PipelineStage.CLASSIFICATION, start, result_count=len(operations.operations)
        )

        # Root-cause analysis (REQ-073-080).
        start = time.perf_counter()
        causality = self._analyzer.analyze(operations, graph)
        timer.record(
            PipelineStage.ROOT_CAUSE, start,
            result_count=len(causality.selected.root_operation_ids),
        )

        # Suppression (REQ-081-089).
        start = time.perf_counter()
        suppression = self._suppressor.suppress(
            norm_source.tree, norm_target.tree, operations, alignment,
            command.suppression_profile,
        )
        timer.record(
            PipelineStage.SUPPRESSION, start,
            result_count=len(suppression.suppressed_effects),
        )

        return ReconciliationResult(
            contract_version=CORE_CONTRACT_VERSION,
            job_id=ctx.job_id,
            complete=complete,
            match_graph=graph,
            alignment=alignment,
            operations=operations,
            causality=causality,
            suppression=suppression,
            diagnostics=tuple(diagnostics),
            metrics=timer.build(),
            profile_versions=self._profile_versions(command),
        )

    # -- Helpers -----------------------------------------------------------

    @staticmethod
    def _duplicate_id_diagnostics(evidence: object) -> list[EngineDiagnostic]:
        from reconciliation.core.evidence.extractor import EvidenceIndex

        assert isinstance(evidence, EvidenceIndex)
        diagnostics: list[EngineDiagnostic] = []
        for side, dups in (
            ("SOURCE", evidence.duplicate_source_ids),
            ("TARGET", evidence.duplicate_target_ids),
        ):
            for persistent_id in sorted(dups):
                diagnostics.append(
                    EngineDiagnostic(
                        code="DUPLICATE_PERSISTENT_ID",
                        severity=Severity.WARNING,
                        stage=PipelineStage.EVIDENCE,
                        message=(
                            f"persistent id is duplicated in the {side.lower()} tree and "
                            "will not be used as authoritative identity"
                        ),
                        metadata={"side": side, "persistent_id": persistent_id},
                    )
                )
        return diagnostics

    @staticmethod
    def _profile_versions(command: ReconcileTreesCommand) -> ProfileVersions:
        return ProfileVersions(
            engine_version=ENGINE_VERSION,
            core_contract_version=CORE_CONTRACT_VERSION,
            normalization_profile_version=command.normalization_profile.version,
            matching_profile_version=command.matching_profile.version,
            alignment_profile_version=command.alignment_profile.version,
            operation_profile_version=command.operation_profile.version,
            suppression_profile_version=command.suppression_profile.version,
        )

    def _incomplete_result(
        self,
        command: ReconcileTreesCommand,
        diagnostics: list[EngineDiagnostic],
        timer: StageTimer,
    ) -> ReconciliationResult:
        from reconciliation.core.contracts.alignment import AlignmentResult
        from reconciliation.core.contracts.causality import (
            CandidateExplanation,
            CausalOperationGraph,
        )
        from reconciliation.core.contracts.evidence import Confidence
        from reconciliation.core.contracts.matches import MatchGraph
        from reconciliation.core.contracts.operations import StructuralOperationSet
        from reconciliation.core.contracts.suppression import SuppressionResult

        empty_explanation = CandidateExplanation(
            explanation_id="explanation-incomplete",
            objective_score=0.0,
            confidence=Confidence(value=0.0),
        )
        return ReconciliationResult(
            contract_version=CORE_CONTRACT_VERSION,
            job_id=command.execution_context.job_id,
            complete=False,
            match_graph=MatchGraph(),
            alignment=AlignmentResult(),
            operations=StructuralOperationSet(),
            causality=CausalOperationGraph(selected=empty_explanation),
            suppression=SuppressionResult(),
            diagnostics=tuple(diagnostics),
            metrics=timer.build(),
            profile_versions=self._profile_versions(command),
        )
