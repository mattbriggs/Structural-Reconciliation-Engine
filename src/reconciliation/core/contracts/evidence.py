"""Evidence and confidence value contracts.

Evidence records make every match, operation, and suppression explainable
(REQ-047, REQ-206-208). Feature *score* and calibrated *confidence* are kept
as distinct values throughout (REQ-046, REQ-278).
"""

from __future__ import annotations

from pydantic import Field

from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.profiles import EvidenceType


class Evidence(StrictModel):
    """A single piece of identity or structural evidence.

    :ivar code: Stable evidence type (REQ-025-030).
    :ivar weight: Contribution weight applied when scoring (>= 0).
    :ivar value: Human-inspectable, non-sensitive summary of the signal (e.g.
        the persistent id or signature string). Callers are responsible for
        redaction of translatable content (REQ-221).
    :ivar source: Which side/context produced the evidence.
    """

    code: EvidenceType
    weight: float = Field(ge=0.0)
    value: str | None = None
    source: str | None = None


class Confidence(StrictModel):
    """A confidence value tagged with calibration status (REQ-277, REQ-278).

    :ivar value: Numeric value in the inclusive range [0, 1].
    :ivar calibrated: Whether ``value`` is a calibrated probability. When
        False the value is a *score*, not a probability.
    :ivar model: Calibration model identifier when calibrated.
    """

    value: float = Field(ge=0.0, le=1.0)
    calibrated: bool = False
    model: str | None = None

    @property
    def is_score(self) -> bool:
        """True when the value must be described as a score, not a probability."""
        return not self.calibrated


class FeatureScore(StrictModel):
    """Aggregate weighted feature score for a candidate correspondence.

    Distinct from :class:`Confidence`: a score summarizes weighted evidence,
    while confidence is the (possibly calibrated) belief derived from it
    (REQ-046).

    :ivar value: Aggregate score in [0, 1].
    :ivar contributions: Per-evidence contributions that produced the score.
    """

    value: float = Field(ge=0.0, le=1.0)
    contributions: tuple[Evidence, ...] = ()
