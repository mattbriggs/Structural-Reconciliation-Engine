"""Identity-evidence extraction (REQ-025-036).

For each node the extractor derives multiple *independent* signals that may
indicate logical identity: persistent id, semantic signature, normalized
label, node type, and child signature. Signals are computed deterministically
from normalized trees so matching never depends on map iteration order
(REQ-203).

Duplicate persistent identifiers are detected here (REQ-035) so the matcher
can refuse to treat a duplicated id as authoritative (AC-010).
"""

from __future__ import annotations

from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.profiles import MatchingProfile
from reconciliation.core.contracts.tree import CanonicalNode, CanonicalTree, NodeRef

#: Default identity property keys the extractor inspects.
DEFAULT_ID_KEYS = ("id", "xml:id", "guid", "key")
DEFAULT_LABEL_KEYS = ("label", "title", "navtitle")


class NodeEvidence(StrictModel):
    """Evidence signals derived for a single node.

    :ivar node_ref: The node these signals describe.
    :ivar node_type: The node's canonical type.
    :ivar persistent_id: First present persistent identifier, if any.
    :ivar label: First present normalized label, if any.
    :ivar signature: Semantic signature from type + sorted identity props.
    :ivar child_signature: Structural signature of child types.
    """

    node_ref: NodeRef
    node_type: str
    persistent_id: str | None = None
    label: str | None = None
    signature: str
    child_signature: str


class EvidenceIndex(StrictModel):
    """All node evidence for both trees, plus duplicate-id detection.

    :ivar source: Node evidence keyed by source node reference.
    :ivar target: Node evidence keyed by target node reference.
    :ivar duplicate_source_ids: Persistent ids that appear more than once in
        the source tree (REQ-035).
    :ivar duplicate_target_ids: Persistent ids duplicated in the target tree.
    """

    source: dict[NodeRef, NodeEvidence]
    target: dict[NodeRef, NodeEvidence]
    duplicate_source_ids: frozenset[str] = frozenset()
    duplicate_target_ids: frozenset[str] = frozenset()

    def is_duplicated(self, persistent_id: str) -> bool:
        """True if ``persistent_id`` is duplicated in either tree."""
        return persistent_id in self.duplicate_source_ids or (
            persistent_id in self.duplicate_target_ids
        )


def _first_present(node: CanonicalNode, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = node.identity_properties.get(key)
        if value is None:
            value = node.content_properties.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _signature(node: CanonicalNode) -> str:
    """Build a semantic signature from type and non-id identity/content props.

    Persistent-id keys are excluded (they are scored separately). Content
    properties are included so that otherwise-identical nodes of the same type
    are distinguishable, and identical repeated nodes share a signature — the
    basis for detecting ambiguity (REQ-026, AC-009).
    """
    parts = [f"type={node.node_type}"]
    for key in sorted(node.identity_properties):
        if key in DEFAULT_ID_KEYS:
            continue
        parts.append(f"id:{key}={node.identity_properties[key]!r}")
    for key in sorted(node.content_properties):
        parts.append(f"content:{key}={node.content_properties[key]!r}")
    return "|".join(parts)


def _child_signature(tree: CanonicalTree, node: CanonicalNode) -> str:
    return ",".join(tree.nodes[c].node_type for c in node.child_refs)


class IdentityEvidenceExtractorService:
    """Default :class:`IdentityEvidenceExtractor` implementation."""

    def extract(
        self,
        source: CanonicalTree,
        target: CanonicalTree,
        profile: MatchingProfile,
    ) -> EvidenceIndex:
        """Extract evidence for both trees.

        :param source: Normalized source tree.
        :param target: Normalized target tree.
        :param profile: Matching profile (reserved for future feature gating).
        :returns: An :class:`EvidenceIndex` with per-node evidence and
            duplicate-id sets.
        """
        source_ev, dup_source = self._extract_tree(source)
        target_ev, dup_target = self._extract_tree(target)
        return EvidenceIndex(
            source=source_ev,
            target=target_ev,
            duplicate_source_ids=dup_source,
            duplicate_target_ids=dup_target,
        )

    @staticmethod
    def _extract_tree(
        tree: CanonicalTree,
    ) -> tuple[dict[NodeRef, NodeEvidence], frozenset[str]]:
        evidence: dict[NodeRef, NodeEvidence] = {}
        id_counts: dict[str, int] = {}
        for node_ref in sorted(tree.nodes):
            node = tree.nodes[node_ref]
            persistent_id = _first_present(node, DEFAULT_ID_KEYS)
            if persistent_id is not None:
                id_counts[persistent_id] = id_counts.get(persistent_id, 0) + 1
            evidence[node_ref] = NodeEvidence(
                node_ref=node_ref,
                node_type=node.node_type,
                persistent_id=persistent_id,
                label=_first_present(node, DEFAULT_LABEL_KEYS),
                signature=_signature(node),
                child_signature=_child_signature(tree, node),
            )
        duplicates = frozenset(k for k, v in id_counts.items() if v > 1)
        return evidence, duplicates
