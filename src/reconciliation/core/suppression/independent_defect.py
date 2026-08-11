"""Independent-defect check (REQ-083, REQ-084, AC-014).

Before a derived effect is suppressed, the affected region is checked for an
*independent* defect — a difference not explained by the root operation, such
as a content change on a node inside a moved subtree. Independent defects must
remain visible even though the surrounding derived path changes are suppressed.
"""

from __future__ import annotations

from reconciliation.core.contracts.operations import StructuralOperationSet
from reconciliation.core.contracts.profiles import OperationType
from reconciliation.core.contracts.tree import NodeRef


def find_independent_defects(
    affected_source_refs: frozenset[NodeRef],
    operations: StructuralOperationSet,
) -> frozenset[NodeRef]:
    """Return source refs in the affected region that carry an independent defect.

    An UPDATE operation on a node within the affected region is treated as an
    independent content defect that must not be suppressed (AC-014).

    :param affected_source_refs: Source refs inside the root operation's region.
    :param operations: All classified operations.
    :returns: The subset of affected refs that have an independent defect.
    """
    defect_refs: set[NodeRef] = set()
    for op in operations.operations:
        if op.type is OperationType.UPDATE:
            for ref in op.source_node_refs:
                if ref in affected_source_refs:
                    defect_refs.add(ref)
    return frozenset(defect_refs)
