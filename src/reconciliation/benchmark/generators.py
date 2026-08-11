"""Synthetic canonical-tree generators for performance and corpus building.

Produces wide, deep, repetitive, and high-edit-density trees. Kept in the
benchmark package (not the test tree, so it is importable by tooling) and
independent of any adapter.
"""

from __future__ import annotations

from reconciliation.core.contracts.tree import CanonicalNode, CanonicalTree
from reconciliation.version import CANONICAL_TREE_CONTRACT_VERSION


def _tree(tree_id: str, nodes: dict[str, CanonicalNode], root: str = "n") -> CanonicalTree:
    return CanonicalTree(
        contract_version=CANONICAL_TREE_CONTRACT_VERSION,
        tree_id=tree_id,
        root_node_ref=root,
        nodes=nodes,
    )


def wide_tree(tree_id: str, n: int) -> CanonicalTree:
    """A root with ``n`` identified topicref children (breadth stress)."""
    children = tuple(f"n.{i}" for i in range(n))
    nodes: dict[str, CanonicalNode] = {
        "n": CanonicalNode(node_ref="n", node_type="map", child_refs=children)
    }
    for i in range(n):
        nodes[f"n.{i}"] = CanonicalNode(
            node_ref=f"n.{i}",
            node_type="topicref",
            parent_ref="n",
            identity_properties={"id": f"k{i}"},
        )
    return _tree(tree_id, nodes)


def deep_tree(tree_id: str, depth: int) -> CanonicalTree:
    """A single chain of ``depth`` nested nodes (depth stress)."""
    nodes: dict[str, CanonicalNode] = {}
    for level in range(depth):
        ref = "n" if level == 0 else f"n{'.0' * level}"
        child = f"n{'.0' * (level + 1)}" if level < depth - 1 else None
        nodes[ref] = CanonicalNode(
            node_ref=ref,
            node_type="map" if level == 0 else "topicref",
            parent_ref=None if level == 0 else ("n" if level == 1 else f"n{'.0' * (level - 1)}"),
            child_refs=(child,) if child else (),
            identity_properties={} if level == 0 else {"id": f"k{level}"},
        )
    return _tree(tree_id, nodes)


def repetitive_tree(tree_id: str, n: int) -> CanonicalTree:
    """A root with ``n`` indistinguishable children (ambiguity/repetition stress)."""
    children = tuple(f"n.{i}" for i in range(n))
    nodes: dict[str, CanonicalNode] = {
        "n": CanonicalNode(node_ref="n", node_type="map", child_refs=children)
    }
    for i in range(n):
        nodes[f"n.{i}"] = CanonicalNode(
            node_ref=f"n.{i}",
            node_type="item",
            parent_ref="n",
            content_properties={"t": "same"},
        )
    return _tree(tree_id, nodes)


def high_edit_density_pair(n: int) -> tuple[CanonicalTree, CanonicalTree]:
    """Return a source/target pair with edits on roughly half the nodes."""
    source = wide_tree("hed-source", n)
    # Target keeps even-indexed ids, drops odd ones, and adds new ones.
    children = []
    nodes: dict[str, CanonicalNode] = {}
    kept = [i for i in range(n) if i % 2 == 0]
    for pos, i in enumerate(kept):
        ref = f"n.{pos}"
        children.append(ref)
        nodes[ref] = CanonicalNode(
            node_ref=ref, node_type="topicref", parent_ref="n",
            identity_properties={"id": f"k{i}"},
        )
    for extra in range(len(kept), len(kept) + n // 4):
        ref = f"n.{extra}"
        children.append(ref)
        nodes[ref] = CanonicalNode(
            node_ref=ref, node_type="topicref", parent_ref="n",
            identity_properties={"id": f"new{extra}"},
        )
    nodes["n"] = CanonicalNode(node_ref="n", node_type="map", child_refs=tuple(children))
    return source, _tree("hed-target", nodes)
