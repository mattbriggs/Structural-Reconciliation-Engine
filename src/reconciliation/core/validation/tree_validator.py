"""Whole-tree invariant validation (REQ-165-170).

Separated from the :class:`~reconciliation.core.contracts.tree.CanonicalTree`
model so that each containment invariant has directly addressable positive
and negative tests. Validation returns a structured
:class:`TreeValidationResult`; :func:`validate_tree` raises
:class:`~reconciliation.core.errors.InvalidTreeError` for callers that want
fail-fast behavior at the job boundary (REQ-005, REQ-174).
"""

from __future__ import annotations

from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.tree import CanonicalTree, NodeRef
from reconciliation.core.errors import InvalidTreeError


class TreeViolation(StrictModel):
    """A single canonical-tree invariant violation.

    :ivar code: Stable violation code (e.g. ``DANGLING_CHILD_REF``).
    :ivar message: Human-readable, non-sensitive description.
    :ivar node_ref: The node the violation concerns, when applicable.
    """

    code: str
    message: str
    node_ref: NodeRef | None = None


class TreeValidationResult(StrictModel):
    """Outcome of validating a canonical tree.

    :ivar valid: True when no violations were detected.
    :ivar violations: Ordered, deterministic list of violations.
    """

    valid: bool
    violations: tuple[TreeViolation, ...] = ()

    def raise_if_invalid(self, *, correlation_id: str | None = None) -> None:
        """Raise :class:`InvalidTreeError` if any violation was recorded.

        :param correlation_id: Optional tracing id attached to the error.
        :raises InvalidTreeError: If the tree is invalid.
        """
        if self.valid:
            return
        first = self.violations[0]
        raise InvalidTreeError(
            f"canonical tree failed validation: {first.message}",
            correlation_id=correlation_id,
            context={
                "violation_count": len(self.violations),
                "violations": [v.model_dump() for v in self.violations],
            },
        )


def _detect_cycles(tree: CanonicalTree) -> list[TreeViolation]:
    """Detect containment cycles by walking parent links to the root (REQ-170)."""
    violations: list[TreeViolation] = []
    for node_ref in sorted(tree.nodes):
        seen: set[NodeRef] = set()
        current: NodeRef | None = node_ref
        while current is not None:
            if current in seen:
                violations.append(
                    TreeViolation(
                        code="CONTAINMENT_CYCLE",
                        message=f"containment cycle detected involving node {node_ref!r}",
                        node_ref=node_ref,
                    )
                )
                break
            seen.add(current)
            node = tree.nodes.get(current)
            if node is None:
                break
            current = node.parent_ref
    return violations


def validate_tree_result(tree: CanonicalTree) -> TreeValidationResult:
    """Validate every whole-tree invariant and return a structured result.

    Checks, in deterministic order:

    * every child reference resolves to an existing node (REQ-166),
    * every non-root parent reference resolves (REQ-166),
    * parent/child links agree bidirectionally,
    * exactly one node (the declared root) has no parent (REQ-169),
    * no containment cycle exists (REQ-170).

    :param tree: The canonical tree to validate.
    :returns: A :class:`TreeValidationResult` listing any violations.
    """
    violations: list[TreeViolation] = []

    # Reference resolvability: children and parents (REQ-166).
    for node_ref in sorted(tree.nodes):
        node = tree.nodes[node_ref]
        for child_ref in node.child_refs:
            if child_ref not in tree.nodes:
                violations.append(
                    TreeViolation(
                        code="DANGLING_CHILD_REF",
                        message=f"node {node_ref!r} references unknown child {child_ref!r}",
                        node_ref=node_ref,
                    )
                )
            else:
                child = tree.nodes[child_ref]
                if child.parent_ref != node_ref:
                    violations.append(
                        TreeViolation(
                            code="PARENT_CHILD_DISAGREEMENT",
                            message=(
                                f"child {child_ref!r} of {node_ref!r} does not point back "
                                f"to it (parent_ref={child.parent_ref!r})"
                            ),
                            node_ref=child_ref,
                        )
                    )
        if node.parent_ref is not None:
            if node.parent_ref not in tree.nodes:
                violations.append(
                    TreeViolation(
                        code="DANGLING_PARENT_REF",
                        message=f"node {node_ref!r} references unknown parent {node.parent_ref!r}",
                        node_ref=node_ref,
                    )
                )
            elif node_ref not in tree.nodes[node.parent_ref].child_refs:
                violations.append(
                    TreeViolation(
                        code="MISSING_FROM_PARENT_CHILDREN",
                        message=(
                            f"node {node_ref!r} is not listed among the children of its "
                            f"parent {node.parent_ref!r}"
                        ),
                        node_ref=node_ref,
                    )
                )

    # Exactly one root: nodes without a parent (REQ-169).
    parentless = sorted(ref for ref, node in tree.nodes.items() if node.parent_ref is None)
    for ref in parentless:
        if ref != tree.root_node_ref:
            violations.append(
                TreeViolation(
                    code="MULTIPLE_ROOTS",
                    message=f"node {ref!r} has no parent but is not the declared root",
                    node_ref=ref,
                )
            )

    violations.extend(_detect_cycles(tree))

    return TreeValidationResult(valid=not violations, violations=tuple(violations))


def validate_tree(tree: CanonicalTree, *, correlation_id: str | None = None) -> None:
    """Validate a tree and raise on the first failure.

    :param tree: The canonical tree to validate.
    :param correlation_id: Optional tracing id attached to a raised error.
    :raises InvalidTreeError: If any invariant is violated.
    """
    validate_tree_result(tree).raise_if_invalid(correlation_id=correlation_id)
