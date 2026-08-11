"""Unit tests for the application error taxonomy."""

from __future__ import annotations

from reconciliation.application.errors import (
    ApplicationError,
    ComparisonRejectedError,
    InvalidPolicyError,
    RecommendationError,
)


def test_error_codes_are_stable() -> None:
    assert ComparisonRejectedError("x").code == "COMPARISON_REJECTED"
    assert InvalidPolicyError("x").code == "INVALID_POLICY"
    assert RecommendationError("x").code == "RECOMMENDATION_ERROR"


def test_error_to_dict_is_safe_and_complete() -> None:
    err = InvalidPolicyError("bad policy", context={"rule": "r1"})
    payload = err.to_dict()
    assert payload == {
        "code": "INVALID_POLICY",
        "message": "bad policy",
        "retryable": False,
        "context": {"rule": "r1"},
    }


def test_code_override() -> None:
    err = ApplicationError("x", code="CUSTOM")
    assert err.code == "CUSTOM"
    assert err.message == "x"
