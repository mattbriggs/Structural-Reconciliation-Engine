"""In-memory builders for canonical trees and default profiles.

These helpers let the whole test suite construct canonical trees and typed
profiles without any XML/DITA/localization dependency, upholding the core
independence boundary (AC-031). They are deliberately small and explicit so
tests read as data, not machinery.
"""

from __future__ import annotations

from reconciliation.core.contracts.commands import (
    ExecutionContext,
    ReconcileTreesCommand,
    ResourceLimits,
)
from reconciliation.core.contracts.profiles import (
    AlignmentProfile,
    AlignmentStrategy,
    EvidenceType,
    FeatureWeight,
    MatchingProfile,
    NormalizationProfile,
    OperationProfile,
    OrderSemantics,
    SuppressionProfile,
    SuppressionRule,
)
from reconciliation.core.contracts.profiles import (
    OperationType as OT,
)
from reconciliation.core.contracts.results import ReconciliationResult
from reconciliation.core.contracts.tree import CanonicalNode, CanonicalTree
from reconciliation.core.engine import DefaultReconciliationEngine
from reconciliation.version import CANONICAL_TREE_CONTRACT_VERSION


class TreeBuilder:
    """Fluent builder for a :class:`CanonicalTree`.

    Example::

        tree = (
            TreeBuilder("t", "root", node_type="map")
            .child("root", "a", node_type="topicref", identity={"id": "a"})
            .child("root", "b", node_type="topicref", identity={"id": "b"})
            .build()
        )
    """

    def __init__(self, tree_id: str, root_ref: str, *, node_type: str = "root") -> None:
        self._tree_id = tree_id
        self._root_ref = root_ref
        self._nodes: dict[str, dict] = {
            root_ref: {
                "node_ref": root_ref,
                "node_type": node_type,
                "parent_ref": None,
                "child_refs": [],
                "identity_properties": {},
                "content_properties": {},
            }
        }

    def child(
        self,
        parent_ref: str,
        node_ref: str,
        *,
        node_type: str = "topicref",
        identity: dict | None = None,
        content: dict | None = None,
    ) -> TreeBuilder:
        """Append a child node under ``parent_ref``."""
        self._nodes[parent_ref]["child_refs"].append(node_ref)
        self._nodes[node_ref] = {
            "node_ref": node_ref,
            "node_type": node_type,
            "parent_ref": parent_ref,
            "child_refs": [],
            "identity_properties": identity or {},
            "content_properties": content or {},
        }
        return self

    def build(self, *, contract_version: str = CANONICAL_TREE_CONTRACT_VERSION) -> CanonicalTree:
        """Materialize the immutable canonical tree."""
        nodes = {
            ref: CanonicalNode(
                node_ref=data["node_ref"],
                node_type=data["node_type"],
                parent_ref=data["parent_ref"],
                child_refs=tuple(data["child_refs"]),
                identity_properties=data["identity_properties"],
                content_properties=data["content_properties"],
            )
            for ref, data in self._nodes.items()
        }
        return CanonicalTree(
            contract_version=contract_version,
            tree_id=self._tree_id,
            root_node_ref=self._root_ref,
            nodes=nodes,
        )


def default_normalization_profile() -> NormalizationProfile:
    """Return a permissive default normalization profile."""
    return NormalizationProfile(profile_id="norm-default", version="v1")


def default_matching_profile() -> MatchingProfile:
    """Return a default matching profile: ID-first, similarity-backed."""
    return MatchingProfile(
        profile_id="match-default",
        version="v1",
        evidence_priority=(
            EvidenceType.PERSISTENT_ID,
            EvidenceType.SEMANTIC_SIGNATURE,
            EvidenceType.NORMALIZED_LABEL,
            EvidenceType.WEIGHTED_SIMILARITY,
            EvidenceType.ANCESTOR_CONTEXT,
        ),
        feature_weights=(
            FeatureWeight(feature=EvidenceType.PERSISTENT_ID, weight=0.5),
            FeatureWeight(feature=EvidenceType.SEMANTIC_SIGNATURE, weight=0.4),
            FeatureWeight(feature=EvidenceType.NORMALIZED_LABEL, weight=0.3),
            FeatureWeight(feature=EvidenceType.WEIGHTED_SIMILARITY, weight=0.2),
        ),
        authoritative_id_features=frozenset({EvidenceType.PERSISTENT_ID}),
        match_threshold=0.6,
        probable_threshold=0.4,
        ambiguity_margin=0.05,
    )


def default_alignment_profile() -> AlignmentProfile:
    """Return a default ordered LCS alignment profile."""
    return AlignmentProfile(
        profile_id="align-default",
        version="v1",
        strategy=AlignmentStrategy.LCS,
        default_order_semantics=OrderSemantics.ORDERED,
    )


def default_operation_profile() -> OperationProfile:
    """Return the default initial-release operation profile."""
    return OperationProfile(profile_id="op-default", version="v1")


def default_suppression_profile() -> SuppressionProfile:
    """Return a default suppression profile covering the common cascades."""
    return SuppressionProfile(
        profile_id="suppress-default",
        version="v1",
        rules=(
            SuppressionRule(
                rule_id="insert-downstream-position-v1",
                root_operation=OT.INSERT,
                effect_category="DOWNSTREAM_POSITION_CHANGED",
                threshold=0.6,
            ),
            SuppressionRule(
                rule_id="delete-downstream-position-v1",
                root_operation=OT.DELETE,
                effect_category="DOWNSTREAM_POSITION_CHANGED",
                threshold=0.6,
            ),
            SuppressionRule(
                rule_id="move-descendant-path-v1",
                root_operation=OT.MOVE,
                effect_category="DESCENDANT_PATH_CHANGED",
                threshold=0.7,
            ),
            SuppressionRule(
                rule_id="reorder-position-v1",
                root_operation=OT.REORDER,
                effect_category="DOWNSTREAM_POSITION_CHANGED",
                threshold=0.6,
            ),
        ),
    )


def reconcile(
    source: CanonicalTree,
    target: CanonicalTree,
    *,
    job_id: str = "job-test",
    correlation_id: str | None = None,
    resource_limits: ResourceLimits | None = None,
    incomplete_on_limit: bool = False,
    operation_profile: OperationProfile | None = None,
    alignment_profile: AlignmentProfile | None = None,
) -> ReconciliationResult:
    """Run the default engine over two trees with default profiles.

    A single convenience entry point for acceptance and integration tests so
    each test reads as data plus an assertion, not pipeline wiring.
    """
    command = ReconcileTreesCommand(
        source_tree=source,
        target_tree=target,
        normalization_profile=default_normalization_profile(),
        matching_profile=default_matching_profile(),
        alignment_profile=alignment_profile or default_alignment_profile(),
        operation_profile=operation_profile or default_operation_profile(),
        suppression_profile=default_suppression_profile(),
        execution_context=ExecutionContext(
            job_id=job_id,
            correlation_id=correlation_id,
            resource_limits=resource_limits or ResourceLimits(),
            incomplete_on_limit=incomplete_on_limit,
        ),
    )
    return DefaultReconciliationEngine().reconcile(command)


def operation_types(result: ReconciliationResult) -> list[str]:
    """Return the sorted operation type names from a result."""
    return sorted(op.type.value for op in result.operations.operations)
