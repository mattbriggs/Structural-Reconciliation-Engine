"""Top-level reconciliation result contract (REQ-171-174, REQ-283).

:class:`ReconciliationResult` is the sole output of the core and the input to
any domain application. It is domain neutral (REQ-171), records the exact
profile/engine versions used (REQ-283, AC-036), and carries a completeness
flag so an explicitly incomplete result is never mistaken for success
(REQ-173, REQ-200).
"""

from __future__ import annotations

from reconciliation.core.contracts.alignment import AlignmentResult
from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.causality import CausalOperationGraph
from reconciliation.core.contracts.diagnostics import EngineDiagnostic
from reconciliation.core.contracts.matches import MatchGraph
from reconciliation.core.contracts.metrics import ReconciliationMetrics
from reconciliation.core.contracts.operations import StructuralOperationSet
from reconciliation.core.contracts.suppression import SuppressionResult


class ProfileVersions(StrictModel):
    """Exact component and profile versions used for a run (REQ-283, AC-036)."""

    engine_version: str
    core_contract_version: str
    normalization_profile_version: str
    matching_profile_version: str
    alignment_profile_version: str
    operation_profile_version: str
    suppression_profile_version: str


class ReconciliationResult(StrictModel):
    """Immutable, domain-neutral result of a reconciliation run.

    :ivar contract_version: Core result contract version (REQ-152).
    :ivar job_id: Comparison job identifier.
    :ivar complete: False when a resource limit or recoverable failure yielded
        an explicitly incomplete result (REQ-173).
    :ivar match_graph: Node correspondences (REQ-038).
    :ivar alignment: Structural alignment (REQ-060).
    :ivar operations: Classified structural operations (REQ-061).
    :ivar causality: Root-cause explanation graph (REQ-073).
    :ivar suppression: Cascade-suppression result (REQ-085).
    :ivar diagnostics: Engine diagnostics (REQ-243).
    :ivar metrics: Stage timings and counts (REQ-199).
    :ivar profile_versions: Exact versions used (REQ-283).

    Determinism note: :meth:`deterministic_fingerprint` excludes volatile
    timing so repeated runs can be compared for semantic stability (AC-012).
    """

    contract_version: str
    job_id: str
    complete: bool = True
    match_graph: MatchGraph
    alignment: AlignmentResult
    operations: StructuralOperationSet
    causality: CausalOperationGraph
    suppression: SuppressionResult
    diagnostics: tuple[EngineDiagnostic, ...] = ()
    metrics: ReconciliationMetrics
    profile_versions: ProfileVersions

    def deterministic_fingerprint(self) -> dict[str, object]:
        """Return a stable, timing-free representation for determinism tests."""
        return {
            "contract_version": self.contract_version,
            "complete": self.complete,
            "matches": [
                {
                    "source": c.source_node_ref,
                    "target": c.target_node_ref,
                    "state": c.state.value,
                }
                for c in self.match_graph.candidates
            ],
            "operations": [
                {
                    "type": op.type.value,
                    "source": list(op.source_node_refs),
                    "target": list(op.target_node_refs),
                }
                for op in self.operations.operations
            ],
            "suppressed": [e.category for e in self.suppression.suppressed_effects],
            "metrics": self.metrics.deterministic_fingerprint(),
        }
