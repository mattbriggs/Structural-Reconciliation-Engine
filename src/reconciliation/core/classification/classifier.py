"""Orchestrating classifier that runs the registry (REQ-061-072).

Builds the default registry (match/update, insert/delete, move, reorder) and
runs each classifier over a shared :class:`ClassificationContext`, then returns
a deterministically ordered :class:`StructuralOperationSet`.
"""

from __future__ import annotations

from reconciliation.core.classification.classifiers.insert_delete import InsertDeleteClassifier
from reconciliation.core.classification.classifiers.match import MatchUpdateClassifier
from reconciliation.core.classification.classifiers.move import MoveClassifier
from reconciliation.core.classification.classifiers.reorder import ReorderClassifier
from reconciliation.core.classification.registry import (
    ClassificationContext,
    ClassifierRegistry,
)
from reconciliation.core.contracts.alignment import AlignmentResult
from reconciliation.core.contracts.matches import MatchGraph
from reconciliation.core.contracts.operations import StructuralOperation, StructuralOperationSet
from reconciliation.core.contracts.profiles import OperationProfile
from reconciliation.core.contracts.tree import CanonicalTree


def default_registry() -> ClassifierRegistry:
    """Return a registry populated with the initial-release classifiers."""
    registry = ClassifierRegistry()
    registry.register(MatchUpdateClassifier())
    registry.register(InsertDeleteClassifier())
    registry.register(MoveClassifier())
    registry.register(ReorderClassifier())
    return registry


class StructuralOperationClassifierService:
    """Default :class:`StructuralOperationClassifier` implementation.

    :param registry: Classifier registry; defaults to :func:`default_registry`.
        Injecting a registry lets callers add classifiers without modifying the
        matcher or aligner (AC-032).
    """

    def __init__(self, registry: ClassifierRegistry | None = None) -> None:
        self._registry = registry or default_registry()

    def classify(
        self,
        source: CanonicalTree,
        target: CanonicalTree,
        graph: MatchGraph,
        alignment: AlignmentResult,
        profile: OperationProfile,
    ) -> StructuralOperationSet:
        """Run all registered classifiers and return their combined output."""
        ctx = ClassificationContext(
            source=source,
            target=target,
            graph=graph,
            alignment=alignment,
            profile=profile,
        )
        operations: list[StructuralOperation] = []
        for classifier in self._registry.classifiers():
            operations.extend(classifier.classify(ctx))
        operations.sort(key=lambda op: (op.type.value, op.operation_id))
        return StructuralOperationSet(operations=tuple(operations))
