"""Engine diagnostic contracts (REQ-173, REQ-243-246).

Diagnostics carry machine codes, severity, and the pipeline stage that
produced them, with safe (non-sensitive) metadata only. They are the vehicle
for reporting an explicitly incomplete result (REQ-173, REQ-200).
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from reconciliation.core.contracts.base import StrictModel


class Severity(str, Enum):
    """Diagnostic severity levels."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class PipelineStage(str, Enum):
    """Ordered core pipeline stages (mirrors the SRS core pipeline)."""

    NORMALIZATION = "NORMALIZATION"
    EVIDENCE = "EVIDENCE"
    MATCHING = "MATCHING"
    ALIGNMENT = "ALIGNMENT"
    CLASSIFICATION = "CLASSIFICATION"
    ROOT_CAUSE = "ROOT_CAUSE"
    SUPPRESSION = "SUPPRESSION"


class EngineDiagnostic(StrictModel):
    """A single diagnostic emitted by the engine.

    :ivar code: Stable machine code.
    :ivar severity: Diagnostic severity.
    :ivar stage: Pipeline stage that produced the diagnostic.
    :ivar message: Non-sensitive human-readable message.
    :ivar metadata: Safe structured metadata (no raw content).
    """

    code: str = Field(min_length=1)
    severity: Severity
    stage: PipelineStage
    message: str
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
