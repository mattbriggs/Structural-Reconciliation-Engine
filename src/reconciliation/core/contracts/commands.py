"""Core command and execution-context contracts (REQ-007, REQ-196-200).

The engine boundary is a single command object. The command carries the two
trees, all four profiles, and an execution context bearing resource limits and
correlation metadata. The command references no locale, DITA, CCMS, HTML, CSV,
or pricing concept (REQ-171).
"""

from __future__ import annotations

from pydantic import Field

from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.profiles import (
    AlignmentProfile,
    MatchingProfile,
    NormalizationProfile,
    OperationProfile,
    SuppressionProfile,
)
from reconciliation.core.contracts.tree import CanonicalTree


class ResourceLimits(StrictModel):
    """Configurable computation limits (REQ-196, REQ-200).

    A value of ``None`` disables the corresponding limit. Exceeding any limit
    yields a controlled failure or explicitly incomplete result.

    :ivar max_node_count: Maximum combined node count.
    :ivar max_tree_depth: Maximum tree depth.
    :ivar max_candidates: Maximum match candidates to generate.
    :ivar max_duration_ms: Maximum wall-clock comparison duration.
    """

    max_node_count: int | None = Field(default=None, ge=1)
    max_tree_depth: int | None = Field(default=None, ge=1)
    max_candidates: int | None = Field(default=None, ge=1)
    max_duration_ms: float | None = Field(default=None, gt=0.0)


class ExecutionContext(StrictModel):
    """Per-run execution metadata (REQ-002, REQ-245).

    :ivar job_id: Unique comparison job identifier (REQ-002).
    :ivar correlation_id: Tracing id propagated across layers (REQ-245).
    :ivar resource_limits: Resource governance limits.
    :ivar incomplete_on_limit: When True, exceeding a limit yields an
        explicitly incomplete result rather than raising (REQ-200).
    """

    job_id: str = Field(min_length=1)
    correlation_id: str | None = None
    resource_limits: ResourceLimits = ResourceLimits()
    incomplete_on_limit: bool = False


class ReconcileTreesCommand(StrictModel):
    """The single input contract to :class:`ReconciliationEngine.reconcile`.

    :ivar source_tree: Authoritative-agnostic source canonical tree.
    :ivar target_tree: Target (e.g. locale) canonical tree.
    :ivar normalization_profile: Normalization rules (REQ-017).
    :ivar matching_profile: Matching configuration (REQ-049).
    :ivar alignment_profile: Alignment configuration (REQ-055).
    :ivar operation_profile: Enabled classifiers and thresholds (REQ-061).
    :ivar suppression_profile: Suppression rules (REQ-082).
    :ivar execution_context: Job/resource/correlation metadata.
    """

    source_tree: CanonicalTree
    target_tree: CanonicalTree
    normalization_profile: NormalizationProfile
    matching_profile: MatchingProfile
    alignment_profile: AlignmentProfile
    operation_profile: OperationProfile
    suppression_profile: SuppressionProfile
    execution_context: ExecutionContext
