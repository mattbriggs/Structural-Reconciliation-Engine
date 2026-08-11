"""Comparison job lifecycle contracts (REQ-001-007, SRS §3.20).

Defines the request DTO, the job lifecycle states, and the job record returned
to callers. Asynchronous execution wraps this at the application boundary; the
reconciliation kernel remains synchronous (REQ-007).
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from reconciliation.application.contracts.common import AuthoritativeSide
from reconciliation.application.contracts.policy import LocaleVariationPolicy
from reconciliation.core.contracts.base import StrictModel
from reconciliation.reporting.contracts import ReportOptions


class ComparisonState(str, Enum):
    """Comparison job lifecycle states (SRS §3.20)."""

    CREATED = "CREATED"
    VALIDATING_INPUTS = "VALIDATING_INPUTS"
    REJECTED = "REJECTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReportFormat(str, Enum):
    """Report artifact formats a job may generate."""

    HTML = "HTML"
    CSV = "CSV"
    JSON = "JSON"


class ComparisonRequest(StrictModel):
    """Input to a localization comparison job (REQ-001, REQ-003, REQ-008).

    :ivar source_content: Source document content.
    :ivar locale_content: Locale document content.
    :ivar locale: Locale code.
    :ivar document_profile_id: Which document profile/adapter to use.
    :ivar authoritative_side: Which tree is authoritative (REQ-008).
    :ivar report_formats: Artifact formats to generate.
    :ivar report_options: Report generation options.
    :ivar policy: Optional locale-variation policy.
    :ivar job_id: Optional caller-supplied job id; generated when absent.
    """

    source_content: str
    locale_content: str
    locale: str = Field(min_length=1)
    document_profile_id: str = Field(min_length=1)
    authoritative_side: AuthoritativeSide = AuthoritativeSide.SOURCE
    report_formats: tuple[ReportFormat, ...] = ()
    report_options: ReportOptions = ReportOptions()
    policy: LocaleVariationPolicy | None = None
    job_id: str | None = None

    @model_validator(mode="after")
    def _policy_locale_matches(self) -> ComparisonRequest:
        if self.policy is not None and self.policy.locale != self.locale:
            raise ValueError("policy locale does not match the comparison locale")
        return self


class ArtifactSummary(StrictModel):
    """A generated artifact's format and reference locator."""

    format: ReportFormat
    name: str
    media_type: str
    location: str | None = None
    size_bytes: int = 0


class JobRecord(StrictModel):
    """The lifecycle record of a comparison job (REQ-002, REQ-246).

    :ivar job_id: Unique job identifier.
    :ivar state: Current lifecycle state.
    :ivar locale: Locale code.
    :ivar status_counts: Summary status counts when completed.
    :ivar direct_issue_count: Number of primary issues when completed.
    :ivar artifacts: Generated artifacts.
    :ivar error_code: Machine error code when rejected/failed.
    :ivar error_message: Safe error message when rejected/failed.
    :ivar correlation_id: Tracing identifier.
    """

    job_id: str
    state: ComparisonState
    locale: str | None = None
    status_counts: dict[str, int] = Field(default_factory=dict)
    direct_issue_count: int = 0
    artifacts: tuple[ArtifactSummary, ...] = ()
    error_code: str | None = None
    error_message: str | None = None
    correlation_id: str | None = None

    @property
    def is_terminal(self) -> bool:
        """True when the job reached a terminal state."""
        return self.state in (
            ComparisonState.COMPLETED,
            ComparisonState.REJECTED,
            ComparisonState.FAILED,
        )
