"""A small built-in labeled corpus (SRS §9.7).

Covers the core reconciliation categories: isolated insertion, deletion,
identifier-preserving update, simple move, sibling reorder, and repeated
indistinguishable structure (ambiguity). This corpus is illustrative — it lets
the benchmark demonstrate structural correctness; it is not a production
calibration corpus (which remains an open question, SRS §10 Q15).
"""

from __future__ import annotations

from reconciliation.benchmark.contracts import ExpectedOperation, LabeledCase
from reconciliation.core.contracts.profiles import OperationType
from reconciliation.core.contracts.tree import CanonicalNode, CanonicalTree
from reconciliation.version import CANONICAL_TREE_CONTRACT_VERSION

#: A node spec: (ref, parent_ref, node_type, id, content).
_Spec = tuple[str, "str | None", str, "str | None", "dict[str, str] | None"]


def _build(tree_id: str, specs: list[_Spec]) -> CanonicalTree:
    children: dict[str, list[str]] = {}
    for ref, parent, _t, _i, _c in specs:
        if parent is not None:
            children.setdefault(parent, []).append(ref)
    nodes: dict[str, CanonicalNode] = {}
    for ref, parent, node_type, node_id, content in specs:
        nodes[ref] = CanonicalNode(
            node_ref=ref,
            node_type=node_type,
            parent_ref=parent,
            child_refs=tuple(children.get(ref, ())),
            identity_properties={"id": node_id} if node_id else {},
            content_properties=dict(content) if content else {},
        )
    return CanonicalTree(
        contract_version=CANONICAL_TREE_CONTRACT_VERSION,
        tree_id=tree_id,
        root_node_ref=specs[0][0],
        nodes=nodes,
    )


def clean_cases() -> tuple[LabeledCase, ...]:
    """Return unambiguous cases with a single known correct interpretation."""
    insertion = LabeledCase(
        case_id="isolated_insertion",
        category="isolated_insertion",
        source_tree=_build(
            "s", [("n", None, "map", None, None),
                  ("n.0", "n", "topicref", "a", None), ("n.1", "n", "topicref", "b", None)]
        ),
        target_tree=_build(
            "t", [("n", None, "map", None, None),
                  ("n.0", "n", "topicref", "a", None), ("n.1", "n", "topicref", "x", None),
                  ("n.2", "n", "topicref", "b", None)]
        ),
        expected_operations=(
            ExpectedOperation(operation_type=OperationType.INSERT, target_ids=frozenset({"x"})),
        ),
        expected_matches=(("a", "a"), ("b", "b")),
    )
    deletion = LabeledCase(
        case_id="isolated_deletion",
        category="isolated_deletion",
        source_tree=_build(
            "s", [("n", None, "map", None, None),
                  ("n.0", "n", "topicref", "a", None), ("n.1", "n", "topicref", "b", None)]
        ),
        target_tree=_build(
            "t", [("n", None, "map", None, None), ("n.0", "n", "topicref", "a", None)]
        ),
        expected_operations=(
            ExpectedOperation(operation_type=OperationType.DELETE, source_ids=frozenset({"b"})),
        ),
        expected_matches=(("a", "a"),),
    )
    update = LabeledCase(
        case_id="identifier_preserving_update",
        category="identifier_preserving_update",
        source_tree=_build(
            "s", [("n", None, "map", None, None),
                  ("n.0", "n", "topicref", "a", {"navtitle": "Hello"})]
        ),
        target_tree=_build(
            "t", [("n", None, "map", None, None),
                  ("n.0", "n", "topicref", "a", {"navtitle": "Bonjour"})]
        ),
        expected_operations=(
            ExpectedOperation(
                operation_type=OperationType.UPDATE,
                source_ids=frozenset({"a"}), target_ids=frozenset({"a"}),
            ),
        ),
        expected_matches=(("a", "a"),),
    )
    move = LabeledCase(
        case_id="simple_move",
        category="simple_move",
        source_tree=_build(
            "s", [("n", None, "map", None, None),
                  ("n.0", "n", "topicref", "p1", None), ("n.1", "n", "topicref", "p2", None),
                  ("n.0.0", "n.0", "topicref", "a", None)]
        ),
        target_tree=_build(
            "t", [("n", None, "map", None, None),
                  ("n.0", "n", "topicref", "p1", None), ("n.1", "n", "topicref", "p2", None),
                  ("n.1.0", "n.1", "topicref", "a", None)]
        ),
        expected_operations=(
            ExpectedOperation(
                operation_type=OperationType.MOVE,
                source_ids=frozenset({"a"}), target_ids=frozenset({"a"}),
            ),
        ),
        expected_matches=(("p1", "p1"), ("p2", "p2"), ("a", "a")),
    )
    reorder = LabeledCase(
        case_id="sibling_reorder",
        category="sibling_reorder",
        source_tree=_build(
            "s", [("n", None, "map", None, None),
                  ("n.0", "n", "topicref", "a", None), ("n.1", "n", "topicref", "b", None)]
        ),
        target_tree=_build(
            "t", [("n", None, "map", None, None),
                  ("n.0", "n", "topicref", "b", None), ("n.1", "n", "topicref", "a", None)]
        ),
        expected_operations=(
            ExpectedOperation(
                operation_type=OperationType.REORDER,
                source_ids=frozenset({"a", "b"}), target_ids=frozenset({"a", "b"}),
            ),
        ),
        expected_matches=(("a", "a"), ("b", "b")),
    )
    return (insertion, deletion, update, move, reorder)


def ambiguous_cases() -> tuple[LabeledCase, ...]:
    """Return cases with intentionally indistinguishable, repeated structure."""
    repeated = LabeledCase(
        case_id="repeated_indistinguishable",
        category="repeated_labels",
        source_tree=_build(
            "s", [("n", None, "map", None, None),
                  ("n.0", "n", "item", None, {"t": "x"}), ("n.1", "n", "item", None, {"t": "x"})]
        ),
        target_tree=_build(
            "t", [("n", None, "map", None, None),
                  ("n.0", "n", "item", None, {"t": "x"}), ("n.1", "n", "item", None, {"t": "x"})]
        ),
        expected_ambiguous_source_ids=frozenset({"n.0", "n.1"}),
    )
    return (repeated,)
