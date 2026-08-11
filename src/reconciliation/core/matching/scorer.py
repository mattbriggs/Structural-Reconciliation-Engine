"""Feature scoring (Strategy pattern, REQ-046, REQ-049).

Produces a :class:`FeatureScore` from independent evidence signals using the
profile's feature weights. Score is deliberately kept distinct from confidence
(REQ-046): this module answers "how much weighted evidence supports the pair",
not "how calibrated-likely is the match".

Translatable-text similarity is intentionally *not* used as an identity signal
when the profile disables it (REQ-050, REQ-113); scoring relies on identifiers,
signatures, and labels, which survive translation.
"""

from __future__ import annotations

from reconciliation.core.contracts.evidence import Evidence, FeatureScore
from reconciliation.core.contracts.profiles import EvidenceType, MatchingProfile
from reconciliation.core.evidence.extractor import NodeEvidence


def _weight_for(profile: MatchingProfile, feature: EvidenceType) -> float:
    for fw in profile.feature_weights:
        if fw.feature == feature:
            return fw.weight
    return 0.0


def score_pair(
    source: NodeEvidence,
    target: NodeEvidence,
    profile: MatchingProfile,
) -> FeatureScore:
    """Compute the weighted feature score for a candidate pair.

    The raw weighted sum is normalized by the total weight of *applicable*
    features so the score stays within [0, 1] regardless of profile weighting.

    :param source: Source node evidence.
    :param target: Target node evidence.
    :param profile: Active matching profile.
    :returns: A normalized :class:`FeatureScore` with per-feature contributions.
    """
    contributions: list[Evidence] = []
    weighted_sum = 0.0
    total_weight = 0.0

    def consider(
        feature: EvidenceType, *, applicable: bool, matched: bool, value: str | None
    ) -> None:
        """Fold one feature into the score.

        A feature only contributes to the denominator when it is *applicable*
        (its signal exists on at least one side). This prevents an absent id or
        label from penalizing nodes that were never expected to carry one — the
        key to preserving ambiguity for id-less repeated structures (AC-009).
        """
        nonlocal weighted_sum, total_weight
        weight = _weight_for(profile, feature)
        if weight <= 0.0 or not applicable:
            return
        total_weight += weight
        if matched:
            weighted_sum += weight
            contributions.append(Evidence(code=feature, weight=weight, value=value))

    # Persistent id equality is the strongest signal.
    id_present = source.persistent_id is not None or target.persistent_id is not None
    id_match = source.persistent_id is not None and source.persistent_id == target.persistent_id
    consider(
        EvidenceType.PERSISTENT_ID,
        applicable=id_present,
        matched=id_match,
        value=source.persistent_id,
    )

    # Semantic signature equality — always applicable (every node has a type).
    consider(
        EvidenceType.SEMANTIC_SIGNATURE,
        applicable=True,
        matched=source.signature == target.signature,
        value=None,
    )

    # Normalized label equality (survives structural change; may differ across
    # locales, so absence of a label match is not disqualifying).
    label_present = source.label is not None or target.label is not None
    label_match = source.label is not None and source.label == target.label
    consider(
        EvidenceType.NORMALIZED_LABEL,
        applicable=label_present,
        matched=label_match,
        value=source.label,
    )

    # Child structural signature — weak structural corroboration, always
    # computable.
    consider(
        EvidenceType.WEIGHTED_SIMILARITY,
        applicable=True,
        matched=source.child_signature == target.child_signature,
        value=None,
    )

    value = weighted_sum / total_weight if total_weight > 0 else 0.0
    return FeatureScore(value=round(value, 6), contributions=tuple(contributions))
