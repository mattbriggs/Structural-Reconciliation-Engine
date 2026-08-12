"""Localization interpretation contracts (REQ-090-116, REQ-150-159, REQ-268-271).

These contracts layer source-to-locale meaning on top of the domain-neutral
core result. A :class:`LocalizationIssue` references the core records it was
derived from (REQ-268) and keeps *node-correspondence* status separate from
*translation-content* status (REQ-091). Repair confidence is absent unless a
recommendation exists (REQ-269), and ``auto_fix_eligible`` is always False in
the initial release (REQ-270).
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from reconciliation.application.contracts.common import AuthoritativeSide
from reconciliation.application.contracts.recommendations import RepairRecommendation
from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.diagnostics import Severity
from reconciliation.core.contracts.results import ReconciliationResult
from reconciliation.core.contracts.tree import NodeRef

__all__ = [
    "AuthoritativeSide",
    "LocalizationIssue",
    "LocalizationStatus",
    "LocalizationSummary",
    "LocalizationValidationResult",
    "NodeCounts",
    "RecommendedAction",
    "TranslationState",
]


class LocalizationStatus(str, Enum):
    """Source-to-locale interpretation statuses (REQ-090-101)."""

    CONFIRMED_MATCH = "CONFIRMED_MATCH"
    PROBABLE_MATCH = "PROBABLE_MATCH"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"
    MISSING_IN_LOCALE = "MISSING_IN_LOCALE"
    EXTRA_IN_LOCALE = "EXTRA_IN_LOCALE"
    WRONG_PARENT = "WRONG_PARENT"
    WRONG_ORDER = "WRONG_ORDER"
    MOVED = "MOVED"
    SOURCE_UPDATED = "SOURCE_UPDATED"
    LOCALE_DIVERGED = "LOCALE_DIVERGED"
    IDENTIFIER_CONFLICT = "IDENTIFIER_CONFLICT"
    EXEMPT_LOCALE_VARIATION = "EXEMPT_LOCALE_VARIATION"


class TranslationState(str, Enum):
    """Translation currency, kept separate from correspondence (REQ-091, REQ-116).

    ``UNKNOWN`` is used when metadata is insufficient to claim current or stale
    (REQ-116, AC-023); the system must never fabricate a currency judgement.
    """

    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class RecommendedAction(str, Enum):
    """Reviewer/correction action suggested for an issue (REQ-158)."""

    NONE = "NONE"
    REVIEW = "REVIEW"
    RELINK_OR_MOVE = "RELINK_OR_MOVE"
    REORDER = "REORDER"
    ADD_OR_TRANSLATE = "ADD_OR_TRANSLATE"
    REVIEW_OR_REMOVE = "REVIEW_OR_REMOVE"
    REVIEW_TRANSLATION = "REVIEW_TRANSLATION"


class LocalizationIssue(StrictModel):
    """One reported correspondence, issue, ambiguity, or exemption (REQ-150).

    :ivar issue_id: Stable identifier.
    :ivar localization_status: The interpreted status.
    :ivar severity: Issue severity.
    :ivar source_node_ref: Source node reference, when applicable.
    :ivar locale_node_ref: Locale node reference, when applicable.
    :ivar source_node_id: Human/domain identifier for the source node.
    :ivar locale_node_id: Human/domain identifier for the locale node.
    :ivar source_label: Human-readable source label.
    :ivar locale_label: Human-readable locale label.
    :ivar core_match_ids: Core match records this issue derives from (REQ-268).
    :ivar core_operation_ids: Core operation records this issue derives from.
    :ivar match_confidence: Node-correspondence confidence (REQ-137).
    :ivar operation_confidence: Structural-diagnosis confidence.
    :ivar repair_confidence: Recommendation-safety confidence; absent when no
        recommendation exists (REQ-269).
    :ivar translation_state: Content currency, independent of correspondence.
    :ivar recommended_action: Suggested action.
    :ivar auto_fix_eligible: Always False for the initial release (REQ-270).
    :ivar policy_exemption: Rule id when the status is an exemption (REQ-271).
    :ivar recommendation_id: Linked recommendation, when one was generated.
    :ivar message: Human-readable, non-sensitive explanation.
    """

    issue_id: str = Field(min_length=1)
    localization_status: LocalizationStatus
    severity: Severity
    source_node_ref: NodeRef | None = None
    locale_node_ref: NodeRef | None = None
    source_node_id: str | None = None
    locale_node_id: str | None = None
    source_label: str | None = None
    locale_label: str | None = None
    core_match_ids: tuple[str, ...] = ()
    core_operation_ids: tuple[str, ...] = ()
    match_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    operation_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    repair_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    translation_state: TranslationState = TranslationState.UNKNOWN
    recommended_action: RecommendedAction = RecommendedAction.NONE
    auto_fix_eligible: bool = False
    policy_exemption: str | None = None
    recommendation_id: str | None = None
    message: str | None = None

    @model_validator(mode="after")
    def _validate_invariants(self) -> LocalizationIssue:
        if self.auto_fix_eligible:
            raise ValueError("auto_fix_eligible must be False in the initial release (REQ-270)")
        if self.recommendation_id is None and self.repair_confidence is not None:
            raise ValueError("repair_confidence must be absent without a recommendation (REQ-269)")
        if (
            self.localization_status is LocalizationStatus.EXEMPT_LOCALE_VARIATION
            and not self.policy_exemption
        ):
            raise ValueError("an exempt issue must identify the applicable policy rule (REQ-271)")
        return self


class NodeCounts(StrictModel):
    """Node-category counts for pricing/effort inputs (REQ-157)."""

    confirmed: int = 0
    probable: int = 0
    ambiguous: int = 0
    missing: int = 0
    extra: int = 0
    structurally_divergent: int = 0
    exempt: int = 0


class LocalizationSummary(StrictModel):
    """Summary counts and rates for a comparison (REQ-156-159).

    :ivar status_counts: Issue counts keyed by localization status.
    :ivar operation_counts: Core operation counts keyed by operation type.
    :ivar action_counts: Recommended-action counts (REQ-158).
    :ivar node_counts: Node-category counts (REQ-157).
    :ivar direct_issue_count: Count of primary (non-suppressed) issues (REQ-159).
    :ivar suppressed_effect_count: Count of suppressed derived effects (REQ-159).
    :ivar unresolved_region_count: Count of sibling regions the core left
        unresolved because correspondence was viable but not uniquely
        resolvable (REQ-058). Reported so uncertainty is visible as uncertainty
        rather than inflated into presence defects.
    """

    status_counts: dict[str, int] = Field(default_factory=dict)
    operation_counts: dict[str, int] = Field(default_factory=dict)
    action_counts: dict[str, int] = Field(default_factory=dict)
    node_counts: NodeCounts = NodeCounts()
    direct_issue_count: int = 0
    suppressed_effect_count: int = 0
    unresolved_region_count: int = 0


class LocalizationValidationResult(StrictModel):
    """Top-level localization result (SRS §4.3, REQ-175-177).

    :ivar contract_version: Localization result contract version (REQ-152).
    :ivar job_id: Comparison job identifier.
    :ivar locale: Locale code for the comparison.
    :ivar authoritative_side: Which tree was treated as authoritative.
    :ivar reconciliation: The immutable core result (REQ-172, REQ-211).
    :ivar issues: Interpreted localization issues.
    :ivar recommendations: Non-executable repair recommendations.
    :ivar summary: Summary counts.
    """

    contract_version: str
    job_id: str
    locale: str
    authoritative_side: AuthoritativeSide
    reconciliation: ReconciliationResult
    issues: tuple[LocalizationIssue, ...] = ()
    recommendations: tuple[RepairRecommendation, ...] = ()
    summary: LocalizationSummary
