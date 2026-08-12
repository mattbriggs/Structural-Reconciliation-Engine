"""Typed, versioned profile contracts that configure core behavior.

Profiles are the sole mechanism by which domain knowledge influences the
domain-neutral core (REQ-017, REQ-049, REQ-253). They are immutable for the
duration of a job (REQ-282) and their exact versions are recorded in results
(REQ-283, REQ-036/AC-036).

Confidence dimensions are kept explicit: every threshold declares which
dimension it applies to (REQ-279) and an uncalibrated model must say so
(REQ-277, REQ-278).
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from reconciliation.core.contracts.base import StrictModel


class ConfidenceDimension(str, Enum):
    """The independent confidence dimensions the system tracks (REQ-276-279)."""

    MATCH = "MATCH"
    OPERATION = "OPERATION"
    SUPPRESSION = "SUPPRESSION"
    REPAIR = "REPAIR"


class EvidenceType(str, Enum):
    """Known identity-evidence signal types (REQ-025-030, REQ-048)."""

    PERSISTENT_ID = "PERSISTENT_ID"
    SEMANTIC_SIGNATURE = "SEMANTIC_SIGNATURE"
    NORMALIZED_LABEL = "NORMALIZED_LABEL"
    NODE_TYPE = "NODE_TYPE"
    CHILD_SIGNATURE = "CHILD_SIGNATURE"
    ANCESTOR_CONTEXT = "ANCESTOR_CONTEXT"
    WEIGHTED_SIMILARITY = "WEIGHTED_SIMILARITY"


class OperationType(str, Enum):
    """Structural operation vocabulary (REQ-061). Extended ops stay disabled."""

    MATCH = "MATCH"
    INSERT = "INSERT"
    DELETE = "DELETE"
    UPDATE = "UPDATE"
    MOVE = "MOVE"
    REORDER = "REORDER"
    # Extended operations (REQ-072) — modeled but disabled by default.
    WRAP = "WRAP"
    UNWRAP = "UNWRAP"
    SPLIT = "SPLIT"
    MERGE = "MERGE"


#: Operations classified in the initial release (REQ-061).
INITIAL_OPERATIONS: frozenset[OperationType] = frozenset(
    {
        OperationType.MATCH,
        OperationType.INSERT,
        OperationType.DELETE,
        OperationType.UPDATE,
        OperationType.MOVE,
        OperationType.REORDER,
    }
)


class CalibrationInfo(StrictModel):
    """Calibration metadata for confidence values (REQ-277, REQ-278).

    :ivar calibrated: Whether numeric values are calibrated probabilities.
    :ivar model: Identifier of the calibration model, if any.

    .. note::
       When ``calibrated`` is False, numeric outputs are *scores*, not
       probabilities, and must be labeled as such downstream.
    """

    calibrated: bool = False
    model: str | None = None

    @model_validator(mode="after")
    def _model_requires_calibration(self) -> CalibrationInfo:
        if self.calibrated and not self.model:
            raise ValueError("calibrated confidence requires a calibration model identifier")
        return self


class Threshold(StrictModel):
    """A named threshold bound to a confidence dimension (REQ-279).

    :ivar dimension: Which confidence dimension this threshold gates.
    :ivar value: Threshold in the inclusive range [0, 1].
    """

    dimension: ConfidenceDimension
    value: float = Field(ge=0.0, le=1.0)


class NormalizationProfile(StrictModel):
    """Rules for removing insignificant variation before matching (REQ-016-024).

    :ivar profile_id: Stable profile identifier.
    :ivar version: Profile version recorded in results (REQ-283).
    :ivar collapse_whitespace: Collapse runs of whitespace in content values
        (REQ-018).
    :ivar ignore_attribute_order: Treat attribute order as insignificant
        (REQ-019).
    :ivar nonsemantic_metadata_keys: Content keys excluded from comparison
        (REQ-020).
    :ivar preserve_property_keys: Keys that must never be altered because they
        are identity/structure/semantically significant (REQ-022).
    """

    profile_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    collapse_whitespace: bool = True
    ignore_attribute_order: bool = True
    nonsemantic_metadata_keys: frozenset[str] = frozenset()
    preserve_property_keys: frozenset[str] = frozenset()

    @model_validator(mode="after")
    def _no_conflicting_rules(self) -> NormalizationProfile:
        """Reject rules that both exclude and preserve the same key (REQ-024)."""
        conflict = self.nonsemantic_metadata_keys & self.preserve_property_keys
        if conflict:
            raise ValueError(
                f"normalization rules conflict: keys both excluded and preserved: "
                f"{sorted(conflict)}"
            )
        return self


class FeatureWeight(StrictModel):
    """Weight assigned to one evidence type in similarity scoring (REQ-049).

    :ivar feature: The evidence signal being weighted.
    :ivar weight: Non-negative contribution weight.
    """

    feature: EvidenceType
    weight: float = Field(ge=0.0)


class MatchingProfile(StrictModel):
    """Configuration for node matching (REQ-037-051, REQ-280-283).

    :ivar profile_id: Stable profile identifier.
    :ivar version: Profile version recorded in results.
    :ivar evidence_priority: Ordered evidence priority (REQ-048). Earlier
        entries dominate.
    :ivar feature_weights: Weights for weighted similarity scoring (REQ-049).
    :ivar authoritative_id_features: Evidence types treated as authoritative
        identity rather than defeasible evidence (REQ-034).
    :ivar hard_constraint_node_type: When True, differing node types are a hard
        incompatibility (REQ-028, REQ-042).
    :ivar match_threshold: Minimum match confidence to confirm (REQ-043).
    :ivar probable_threshold: Minimum confidence for a probable (non-confirmed)
        match. Must not exceed ``match_threshold``.
    :ivar ambiguity_margin: Score window within which competing candidates are
        retained as ambiguous (REQ-044).
    :ivar disable_similarity_for_translatable: Do not use content similarity of
        translatable text as an identity signal (REQ-050, REQ-113).
    :ivar tie_break_keys: Deterministic tie-break ordering keys (REQ-045,
        REQ-204).
    :ivar calibration: Calibration metadata for match confidence.
    """

    profile_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    evidence_priority: tuple[EvidenceType, ...]
    feature_weights: tuple[FeatureWeight, ...] = ()
    authoritative_id_features: frozenset[EvidenceType] = frozenset()
    hard_constraint_node_type: bool = True
    match_threshold: float = Field(ge=0.0, le=1.0)
    probable_threshold: float = Field(ge=0.0, le=1.0)
    ambiguity_margin: float = Field(ge=0.0, le=1.0)
    disable_similarity_for_translatable: bool = True
    tie_break_keys: tuple[str, ...] = ("source_node_ref", "target_node_ref")
    calibration: CalibrationInfo = CalibrationInfo()

    @model_validator(mode="after")
    def _validate(self) -> MatchingProfile:
        if not self.evidence_priority:
            raise ValueError("evidence_priority must not be empty")
        if len(set(self.evidence_priority)) != len(self.evidence_priority):
            raise ValueError("evidence_priority must not contain duplicates")
        if self.probable_threshold > self.match_threshold:
            raise ValueError("probable_threshold must not exceed match_threshold")
        if not self.tie_break_keys:
            raise ValueError("tie_break_keys must define a deterministic ordering")
        return self


class OrderSemantics(str, Enum):
    """Whether sibling order carries meaning for a node type (REQ-054, REQ-097)."""

    ORDERED = "ORDERED"
    UNORDERED = "UNORDERED"


class AlignmentStrategy(str, Enum):
    """Supported sequence-alignment strategies (REQ-055)."""

    LCS = "LCS"
    WEIGHTED_DP = "WEIGHTED_DP"


class AlignmentProfile(StrictModel):
    """Configuration for structural alignment (REQ-052-060).

    :ivar profile_id: Stable profile identifier.
    :ivar version: Profile version recorded in results.
    :ivar strategy: Sequence-alignment strategy to apply.
    :ivar default_order_semantics: Order semantics for node types not listed
        in ``order_semantics_by_type``.
    :ivar order_semantics_by_type: Per-node-type order semantics overrides.
    :ivar use_anchor_partitioning: Enable stable-anchor partitioning of large
        regions (REQ-057, REQ-198).

    .. note::
       The current aligner implements ``LCS`` only, and confirmed matches act as
       its structural anchors implicitly, so ``use_anchor_partitioning`` is
       advisory. Requesting an unimplemented ``strategy`` does not silently
       change behavior: the engine emits an
       ``ALIGNMENT_STRATEGY_NOT_IMPLEMENTED`` diagnostic and applies LCS.
    """

    profile_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    strategy: AlignmentStrategy = AlignmentStrategy.LCS
    default_order_semantics: OrderSemantics = OrderSemantics.ORDERED
    order_semantics_by_type: dict[str, OrderSemantics] = Field(default_factory=dict)
    use_anchor_partitioning: bool = True

    def order_semantics_for(self, node_type: str) -> OrderSemantics:
        """Return the order semantics configured for ``node_type``."""
        return self.order_semantics_by_type.get(node_type, self.default_order_semantics)


class UnresolvedPresencePolicy(str, Enum):
    """How presence operations behave where alignment is unresolved (REQ-058).

    ``INSERT`` and ``DELETE`` mean "no viable correspondence exists". A node
    that participates in ambiguous candidate correspondences has a viable
    correspondence that is merely not uniquely resolvable, so asserting absence
    for it would be a precise lie. This policy names the escape hatches
    explicitly instead of leaving the behavior implicit:

    - ``SUPPRESS_AMBIGUOUS_NODES`` (default): withhold INSERT/DELETE for nodes
      participating in ambiguous candidates; other nodes in the same region are
      still diagnosed, so a real defect beside an ambiguity is not swallowed.
    - ``SUPPRESS_UNRESOLVED_REGIONS``: withhold INSERT/DELETE for every node in
      a region containing any unresolved position — maximally cautious.
    - ``EMIT_ALL``: treat unresolved positions as absent (pre-unresolved-path
      behavior). Retained for callers that must have a total interpretation and
      accept the false positives that come with it.
    """

    SUPPRESS_AMBIGUOUS_NODES = "SUPPRESS_AMBIGUOUS_NODES"
    SUPPRESS_UNRESOLVED_REGIONS = "SUPPRESS_UNRESOLVED_REGIONS"
    EMIT_ALL = "EMIT_ALL"


class OperationProfile(StrictModel):
    """Enabled classifiers and operation-specific thresholds (REQ-061-072).

    :ivar profile_id: Stable profile identifier.
    :ivar version: Profile version recorded in results.
    :ivar enabled_operations: Operations permitted to be classified. Extended
        operations are rejected unless explicitly enabled (REQ-072).
    :ivar move_confidence_threshold: Minimum match confidence to classify a
        MOVE rather than DELETE+INSERT (REQ-070, REQ-071).
    :ivar unresolved_presence_policy: Whether unresolved correspondence may be
        reported as a presence defect (REQ-058, REQ-071).
    :ivar operation_thresholds: Additional per-operation confidence thresholds.
    """

    profile_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    enabled_operations: frozenset[OperationType] = INITIAL_OPERATIONS
    move_confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    unresolved_presence_policy: UnresolvedPresencePolicy = (
        UnresolvedPresencePolicy.SUPPRESS_AMBIGUOUS_NODES
    )
    operation_thresholds: tuple[Threshold, ...] = ()

    @model_validator(mode="after")
    def _reject_disabled_extended(self) -> OperationProfile:
        extended = {
            OperationType.WRAP,
            OperationType.UNWRAP,
            OperationType.SPLIT,
            OperationType.MERGE,
        }
        enabled_extended = self.enabled_operations & extended
        if enabled_extended:
            raise ValueError(
                "extended operations are disabled in the initial release: "
                f"{sorted(op.value for op in enabled_extended)}"
            )
        return self


class SuppressionRule(StrictModel):
    """A single cascade-suppression rule (REQ-081-089).

    :ivar rule_id: Stable, versioned rule identifier.
    :ivar root_operation: Root operation type this rule reacts to.
    :ivar effect_category: Category of derived effect it suppresses.
    :ivar threshold: Minimum root-operation confidence to suppress (REQ-081).
    """

    rule_id: str = Field(min_length=1)
    root_operation: OperationType
    effect_category: str = Field(min_length=1)
    threshold: float = Field(ge=0.0, le=1.0)


class SuppressionProfile(StrictModel):
    """Configuration for cascade suppression (REQ-081-089).

    :ivar profile_id: Stable profile identifier.
    :ivar version: Profile version recorded in results.
    :ivar rules: Suppression rules; rule ids must be unique.
    :ivar independent_defect_check: Require an independent-defect check before
        suppressing (REQ-083, REQ-084).
    """

    profile_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    rules: tuple[SuppressionRule, ...] = ()
    independent_defect_check: bool = True

    @model_validator(mode="after")
    def _unique_rule_ids(self) -> SuppressionProfile:
        ids = [r.rule_id for r in self.rules]
        if len(set(ids)) != len(ids):
            raise ValueError("suppression rule ids must be unique")
        return self

    def rules_for(self, operation: OperationType) -> tuple[SuppressionRule, ...]:
        """Return suppression rules keyed to ``operation``."""
        return tuple(r for r in self.rules if r.root_operation == operation)
