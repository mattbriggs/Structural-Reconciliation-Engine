"""Tabular report contracts (REQ-150-153, REQ-155).

A :class:`ReportRow` is one reported correspondence, issue, ambiguity, or
suppressed effect (REQ-150) carrying stable identifiers that link it back to
the job and to core operations (REQ-151). :class:`ReportTable` is the versioned
container (REQ-152). The column set follows the SRS §3.18 field table.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import Field

from reconciliation.core.contracts.base import StrictModel


class ReportOptions(StrictModel):
    """Options controlling report generation.

    :ivar include_suppressed: Emit suppressed-effect rows (REQ-088). They are
        never discarded from the underlying result regardless of this flag.
    :ivar redact_content: Replace human labels/messages with placeholders so a
        shared report reveals no source or translated text (REQ-221, REQ-226).
    """

    include_suppressed: bool = True
    redact_content: bool = False


class ReportRow(StrictModel):
    """One flattened report row (SRS §3.18 field table).

    Every field is optional except the linking identifiers so a row can
    represent a correspondence, an issue, an ambiguity, or a suppressed effect.
    """

    job_id: str
    result_id: str = Field(min_length=1)
    source_node_id: str | None = None
    locale_node_id: str | None = None
    source_path: str | None = None
    locale_path: str | None = None
    node_type: str | None = None
    source_label: str | None = None
    locale_label: str | None = None
    match_status: str | None = None
    localization_status: str | None = None
    operation: str | None = None
    match_confidence: float | None = None
    operation_confidence: float | None = None
    repair_confidence: float | None = None
    evidence_codes: tuple[str, ...] = ()
    source_revision: str | None = None
    locale_revision: str | None = None
    root_operation_id: str | None = None
    is_suppressed: bool = False
    suppression_rule: str | None = None
    suppressed_effect_count: int = 0
    recommended_action: str | None = None
    auto_fix_eligible: bool = False
    reviewer_decision: str | None = None
    policy_exemption: str | None = None
    message: str | None = None


class ReportTable(StrictModel):
    """Versioned tabular report (REQ-152).

    :ivar schema_version: Report contract version.
    :ivar job_id: Comparison job identifier.
    :ivar rows: The report rows in deterministic order.
    """

    schema_version: str
    job_id: str
    rows: tuple[ReportRow, ...] = ()

    @staticmethod
    def columns() -> tuple[str, ...]:
        """Return the ordered column names for tabular serialization."""
        return tuple(ReportRow.model_fields.keys())


class ReportRenderer(Protocol):
    """Structural contract for a report renderer (REQ-229)."""

    #: Stable media type produced by the renderer.
    media_type: str

    def render(self, table: ReportTable) -> str:
        """Render a report table to its serialized form."""
        ...
