"""Unit tests for profile contracts and cross-profile validation.

Covers REQ-024 (normalization conflict), REQ-072 (extended ops disabled),
REQ-279 (threshold dimension), and REQ-280-283 (profile validation).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from reconciliation.core.contracts.profiles import (
    CalibrationInfo,
    EvidenceType,
    MatchingProfile,
    NormalizationProfile,
    OperationProfile,
    OperationType,
    SuppressionProfile,
    SuppressionRule,
)
from reconciliation.core.validation.profile_validator import validate_profiles
from tests.builders import (
    default_matching_profile,
    default_operation_profile,
    default_suppression_profile,
)


def test_normalization_conflict_rejected() -> None:
    # REQ-024: same key both excluded and preserved is a profile error.
    with pytest.raises(ValidationError):
        NormalizationProfile(
            profile_id="n",
            version="v1",
            nonsemantic_metadata_keys=frozenset({"k"}),
            preserve_property_keys=frozenset({"k"}),
        )


def test_extended_operations_disabled() -> None:
    # REQ-072: extended ops cannot be enabled in the initial release.
    with pytest.raises(ValidationError):
        OperationProfile(
            profile_id="op",
            version="v1",
            enabled_operations=frozenset({OperationType.WRAP}),
        )


def test_probable_threshold_cannot_exceed_match_threshold() -> None:
    with pytest.raises(ValidationError):
        MatchingProfile(
            profile_id="m",
            version="v1",
            evidence_priority=(EvidenceType.PERSISTENT_ID,),
            match_threshold=0.5,
            probable_threshold=0.7,
            ambiguity_margin=0.05,
        )


def test_calibrated_confidence_requires_model() -> None:
    # REQ-277/278
    with pytest.raises(ValidationError):
        CalibrationInfo(calibrated=True, model=None)


def test_duplicate_suppression_rule_ids_rejected() -> None:
    with pytest.raises(ValidationError):
        SuppressionProfile(
            profile_id="s",
            version="v1",
            rules=(
                SuppressionRule(
                    rule_id="dup", root_operation=OperationType.MOVE,
                    effect_category="X", threshold=0.5,
                ),
                SuppressionRule(
                    rule_id="dup", root_operation=OperationType.INSERT,
                    effect_category="Y", threshold=0.5,
                ),
            ),
        )


def test_cross_profile_validation_passes_for_defaults() -> None:
    result = validate_profiles(
        default_matching_profile(),
        default_operation_profile(),
        default_suppression_profile(),
    )
    assert result.valid


def test_suppression_rule_targeting_disabled_operation_fails() -> None:
    # Operation profile that only enables MATCH/INSERT, but a rule targets MOVE.
    op = OperationProfile(
        profile_id="op",
        version="v1",
        enabled_operations=frozenset({OperationType.MATCH, OperationType.INSERT}),
    )
    suppression = SuppressionProfile(
        profile_id="s",
        version="v1",
        rules=(
            SuppressionRule(
                rule_id="r", root_operation=OperationType.MOVE,
                effect_category="X", threshold=0.5,
            ),
        ),
    )
    result = validate_profiles(default_matching_profile(), op, suppression)
    assert not result.valid
    assert result.violations[0].code == "SUPPRESSION_RULE_DISABLED_OPERATION"
