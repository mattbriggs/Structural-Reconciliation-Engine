"""Confidence derivation (REQ-046, REQ-276-279).

Wraps a feature score in a :class:`Confidence` value carrying calibration
metadata. In the initial release confidence is *uncalibrated*: the numeric
value equals the score and is therefore a **score, not a probability**
(REQ-278). When a calibration model is supplied by profile, this is the single
place to apply it — callers never fabricate calibrated probabilities.
"""

from __future__ import annotations

from reconciliation.core.contracts.evidence import Confidence, FeatureScore
from reconciliation.core.contracts.profiles import CalibrationInfo


def derive_confidence(score: FeatureScore, calibration: CalibrationInfo) -> Confidence:
    """Derive a match confidence from a feature score.

    :param score: The weighted feature score.
    :param calibration: Calibration metadata from the matching profile.
    :returns: A :class:`Confidence`; ``calibrated`` mirrors the profile and,
        when False, the value is labeled a score via
        :attr:`Confidence.is_score`.
    """
    return Confidence(
        value=score.value,
        calibrated=calibration.calibrated,
        model=calibration.model,
    )
