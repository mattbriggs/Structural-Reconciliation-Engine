"""Unit tests for application contract invariants (REQ-124/125/269-275)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from reconciliation.application.contracts.common import AuthoritativeSide
from reconciliation.application.contracts.localization import (
    LocalizationIssue,
    LocalizationStatus,
)
from reconciliation.application.contracts.policy import (
    LocaleVariationPolicy,
    LocaleVariationRule,
)
from reconciliation.application.contracts.recommendations import (
    RepairChange,
    RepairOperation,
    RepairRecommendation,
)
from reconciliation.core.contracts.diagnostics import Severity
from reconciliation.core.contracts.profiles import OperationType


def test_issue_auto_fix_must_be_false() -> None:
    with pytest.raises(ValidationError):
        LocalizationIssue(
            issue_id="i",
            localization_status=LocalizationStatus.CONFIRMED_MATCH,
            severity=Severity.INFO,
            auto_fix_eligible=True,
        )


def test_repair_confidence_requires_recommendation() -> None:
    # REQ-269: repair_confidence absent when no recommendation exists.
    with pytest.raises(ValidationError):
        LocalizationIssue(
            issue_id="i",
            localization_status=LocalizationStatus.WRONG_PARENT,
            severity=Severity.ERROR,
            repair_confidence=0.5,
            recommendation_id=None,
        )


def test_exempt_issue_requires_policy_rule() -> None:
    # REQ-271
    with pytest.raises(ValidationError):
        LocalizationIssue(
            issue_id="i",
            localization_status=LocalizationStatus.EXEMPT_LOCALE_VARIATION,
            severity=Severity.INFO,
            policy_exemption=None,
        )


def _recommendation(**overrides) -> RepairRecommendation:
    base = dict(
        recommendation_id="r",
        operation=RepairOperation.MOVE_NODE,
        authoritative_side=AuthoritativeSide.SOURCE,
        target_side=AuthoritativeSide.LOCALE,
        issue_id="i",
        repair_confidence=0.5,
        changes=frozenset({RepairChange.CONTAINMENT}),
        preconditions=("INPUT_FINGERPRINT_UNCHANGED",),
    )
    base.update(overrides)
    return RepairRecommendation(**base)


def test_recommendation_cannot_be_executable() -> None:
    # REQ-125 / AC-037
    with pytest.raises(ValidationError):
        _recommendation(executable=True)


def test_recommendation_cannot_be_auto_fix() -> None:
    # REQ-124
    with pytest.raises(ValidationError):
        _recommendation(auto_fix_eligible=True)


def test_recommendation_requires_preconditions() -> None:
    # AC-039
    with pytest.raises(ValidationError):
        _recommendation(preconditions=())


def test_recommendation_requires_changes() -> None:
    # REQ-275
    with pytest.raises(ValidationError):
        _recommendation(changes=frozenset())


def test_valid_recommendation_constructs() -> None:
    rec = _recommendation()
    assert rec.executable is False
    assert RepairChange.CONTAINMENT in rec.changes


def test_policy_rejects_duplicate_rule_ids() -> None:
    with pytest.raises(ValidationError):
        LocaleVariationPolicy(
            policy_id="p",
            version="v1",
            locale="fr-FR",
            rules=(
                LocaleVariationRule(
                    rule_id="dup", permitted_operation=OperationType.INSERT,
                    justification="x",
                ),
                LocaleVariationRule(
                    rule_id="dup", permitted_operation=OperationType.DELETE,
                    justification="y",
                ),
            ),
        )


def test_policy_rule_applies_to() -> None:
    rule = LocaleVariationRule(
        rule_id="r",
        permitted_operation=OperationType.INSERT,
        node_types=frozenset({"topicref"}),
        justification="x",
    )
    assert rule.applies_to(OperationType.INSERT, "topicref")
    assert not rule.applies_to(OperationType.INSERT, "keydef")
    assert not rule.applies_to(OperationType.DELETE, "topicref")
