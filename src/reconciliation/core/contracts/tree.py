"""Canonical tree contract consumed by the reconciliation core.

The core never sees raw XML. Domain adapters convert their source models into
the domain-neutral :class:`CanonicalTree` defined here (REQ-009–014). This
module defines the *shape* and *structural invariants* of that contract;
richer cross-node validation (cycles, dangling references, uniqueness) lives
in :mod:`reconciliation.core.validation.tree_validator` so that construction
and full validation can be exercised independently.

Structural invariants enforced at model level:

* every non-root node has exactly one parent (REQ-167),
* the root has no parent (REQ-169),
* a node does not appear twice in one parent's child list (REQ-168).

Cross-node invariants (reference resolvability REQ-166, acyclicity REQ-170,
parent/child agreement) are enforced by the tree validator because they need
the whole node map.
"""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from reconciliation.core.contracts.base import ExtensibleModel, StrictModel

#: Opaque, stable, per-tree runtime reference to a node. Adapters assign these;
#: the core treats them as identity-free handles (REQ-010).
NodeRef = str

#: Recursive JSON-like value space for canonical properties (REQ-010), mirroring
#: the SRS ``CanonicalValue`` definition. Values must be serializable so that
#: results remain auditable and reproducible. Declared as a PEP 695 ``type``
#: alias so Pydantic resolves the self-reference without infinite recursion.
type CanonicalValue = (
    str | int | float | bool | list[CanonicalValue] | dict[str, CanonicalValue] | None
)


class SourceLocation(StrictModel):
    """Original input location for a canonical node.

    Preserved so reports can point back to concrete source and locale XML
    (REQ-013). All fields are optional because not every adapter can supply
    positional metadata.

    :ivar document_uri: Identifier of the originating document, if known.
    :ivar line: 1-based line number when available.
    :ivar column: 1-based column number when available.
    :ivar xpath: Structural path within the source document when available.
    """

    document_uri: str | None = None
    line: int | None = Field(default=None, ge=1)
    column: int | None = Field(default=None, ge=1)
    xpath: str | None = None


class CanonicalNode(ExtensibleModel):
    """A single node in a canonical tree.

    Property values are partitioned by the *role* the adapter assigns them so
    that matching, content comparison, ordering, and validation can select
    the relevant dimension independently (REQ-012, REQ-032 of the SRS problem
    statement: identity, content, hierarchy, order, structure are separate).

    :ivar node_ref: Stable runtime reference, unique within the tree.
    :ivar node_type: Canonical or domain node type used for hard
        compatibility constraints and as identity evidence (REQ-028).
    :ivar parent_ref: Parent reference, or ``None`` for the root (REQ-167,
        REQ-169).
    :ivar child_refs: Ordered child references; order is significant only for
        node types the profile declares ordered (REQ-054).
    :ivar identity_properties: Properties that may contribute to logical
        identity (persistent IDs, keys, signatures inputs).
    :ivar content_properties: Properties compared for content/translation
        state, excluded from structural identity when the profile says so.
    :ivar structural_properties: Properties describing structure/containment.
    :ivar extension_properties: Adapter-specific metadata the kernel does not
        interpret (REQ-014).
    :ivar source_location: Original input location when available.
    """

    node_ref: NodeRef = Field(min_length=1)
    node_type: str = Field(min_length=1)
    parent_ref: NodeRef | None = None
    child_refs: tuple[NodeRef, ...] = ()
    identity_properties: dict[str, CanonicalValue] = Field(default_factory=dict)
    content_properties: dict[str, CanonicalValue] = Field(default_factory=dict)
    structural_properties: dict[str, CanonicalValue] = Field(default_factory=dict)
    extension_properties: dict[str, CanonicalValue] = Field(default_factory=dict)
    source_location: SourceLocation | None = None

    @field_validator("child_refs")
    @classmethod
    def _unique_children(cls, value: tuple[NodeRef, ...]) -> tuple[NodeRef, ...]:
        """Reject a node appearing more than once in its child list (REQ-168)."""
        if len(set(value)) != len(value):
            raise ValueError("child_refs must not contain duplicate node references")
        return value

    @model_validator(mode="after")
    def _node_not_own_parent(self) -> CanonicalNode:
        """Reject the trivial self-cycle where a node is its own parent."""
        if self.parent_ref is not None and self.parent_ref == self.node_ref:
            raise ValueError(f"node {self.node_ref!r} cannot be its own parent")
        if self.node_ref in self.child_refs:
            raise ValueError(f"node {self.node_ref!r} cannot be its own child")
        return self


class CanonicalTree(StrictModel):
    """Immutable rooted tree consumed by the reconciliation engine.

    The tree is frozen for the duration of a comparison (REQ-165, REQ-282).
    Model-level validation checks version support, root presence, and that
    the root reference resolves; the full battery of containment invariants
    (REQ-166, REQ-170) is applied by the tree validator.

    :ivar contract_version: Version of the canonical tree contract (REQ-009).
    :ivar tree_id: Stable identifier for this tree.
    :ivar root_node_ref: Reference to the root node.
    :ivar nodes: Mapping of node reference to node. Ordering of this mapping
        must never influence results (REQ-203).
    :ivar metadata: Free-form tree-level metadata (fingerprints, adapter
        version); not interpreted by the kernel.
    """

    contract_version: str = Field(min_length=1)
    tree_id: str = Field(min_length=1)
    root_node_ref: NodeRef = Field(min_length=1)
    nodes: dict[NodeRef, CanonicalNode]
    metadata: dict[str, CanonicalValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _root_present_and_consistent(self) -> CanonicalTree:
        """Ensure the tree is non-empty and the declared root resolves.

        Deeper structural checks are intentionally deferred to the tree
        validator so that a caller can construct a syntactically valid tree
        and then run explicit, individually-testable invariant checks.
        """
        if not self.nodes:
            raise ValueError("canonical tree must contain at least the root node")
        if self.root_node_ref not in self.nodes:
            raise ValueError(f"root_node_ref {self.root_node_ref!r} is not present in nodes")
        root = self.nodes[self.root_node_ref]
        if root.parent_ref is not None:
            raise ValueError("root node must not have a parent (REQ-169)")
        # Ensure every node's declared node_ref agrees with its map key.
        for key, node in self.nodes.items():
            if key != node.node_ref:
                raise ValueError(
                    f"node map key {key!r} does not match node_ref {node.node_ref!r}"
                )
        return self

    def child_nodes(self, node_ref: NodeRef) -> tuple[CanonicalNode, ...]:
        """Return the ordered child nodes of ``node_ref``.

        :param node_ref: Reference whose children are requested.
        :returns: Child nodes in declared order.
        :raises KeyError: If ``node_ref`` or any child reference is unknown.
        """
        return tuple(self.nodes[ref] for ref in self.nodes[node_ref].child_refs)
