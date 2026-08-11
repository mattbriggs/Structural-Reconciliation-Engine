"""Tests for the pricing boundary (REQ-160-164, AC-035)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from reconciliation.application.contracts.pricing import (
    CategoryRate,
    PricingProfile,
)
from reconciliation.application.services.pricing import (
    PricingAssessmentService,
    build_pricing_inputs,
)
from tests.app_builders import localize
from tests.builders import TreeBuilder


def _result(job_id: str = "price-job"):
    # 1 confirmed (a), 2 missing (b, c).
    src = TreeBuilder("s", "r", node_type="map")
    src.child("r", "a", identity={"id": "a"}).child("r", "b", identity={"id": "b"}).child(
        "r", "c", identity={"id": "c"}
    )
    tgt = TreeBuilder("t", "r", node_type="map")
    tgt.child("r", "a", identity={"id": "a"})
    return localize(src.build(), tgt.build(), job_id=job_id)


def _profile(currency: str = "USD", *, missing_price: str = "40") -> PricingProfile:
    return PricingProfile(
        profile_id="std",
        version="v1",
        currency=currency,
        rates=(
            CategoryRate(category="missing", effort_hours=0.5, unit_price=Decimal(missing_price)),
            CategoryRate(category="confirmed", effort_hours=0.1, unit_price=Decimal("5")),
        ),
    )


def test_build_inputs_from_summary() -> None:
    inputs = build_pricing_inputs(_result())
    # Consumes the versioned report contract, not engine internals (REQ-162).
    assert inputs.report_contract_version == "localization-result-v1"
    assert inputs.missing == 2
    assert inputs.confirmed == 1


def test_assess_computes_effort_and_price() -> None:
    inputs = build_pricing_inputs(_result())
    assessment = PricingAssessmentService().assess(inputs, _profile())
    # 2*40 + 1*5 = 85; effort 2*0.5 + 1*0.1 = 1.1.
    assert assessment.estimated_price.amount == Decimal("85")
    assert assessment.estimated_price.currency == "USD"
    assert assessment.effort.total_hours == pytest.approx(1.1)
    assert assessment.pricing_profile_version == "v1"
    # Measured facts are retained alongside the estimate (REQ-163, REQ-164).
    assert assessment.inputs.missing == 2
    assert assessment.price_breakdown["missing"].amount == Decimal("80")


def test_profile_rejects_unknown_category() -> None:
    with pytest.raises(ValidationError):
        PricingProfile(
            profile_id="p", version="v1", currency="USD",
            rates=(CategoryRate(category="nonsense", effort_hours=1.0, unit_price=Decimal("1")),),
        )


def test_profile_rejects_duplicate_category() -> None:
    with pytest.raises(ValidationError):
        PricingProfile(
            profile_id="p", version="v1", currency="USD",
            rates=(
                CategoryRate(category="missing", effort_hours=1.0, unit_price=Decimal("1")),
                CategoryRate(category="missing", effort_hours=2.0, unit_price=Decimal("2")),
            ),
        )


def test_ac_035_pricing_changes_do_not_alter_reconciliation() -> None:
    result = _result()
    fingerprint = result.reconciliation.deterministic_fingerprint()
    statuses = tuple(i.localization_status for i in result.issues)

    service = PricingAssessmentService()
    inputs = build_pricing_inputs(result)
    cheap = service.assess(inputs, _profile(missing_price="40"))
    pricey = service.assess(inputs, _profile(currency="EUR", missing_price="900"))

    # Different pricing, but the reconciliation result is untouched (AC-035).
    assert cheap.estimated_price.amount != pricey.estimated_price.amount
    assert result.reconciliation.deterministic_fingerprint() == fingerprint
    assert tuple(i.localization_status for i in result.issues) == statuses


def test_zero_count_categories_are_skipped() -> None:
    inputs = build_pricing_inputs(_result())
    # A profile pricing only 'ambiguous' (count 0) yields zero price.
    profile = PricingProfile(
        profile_id="amb", version="v1", currency="USD",
        rates=(CategoryRate(category="ambiguous", effort_hours=3.0, unit_price=Decimal("100")),),
    )
    assessment = PricingAssessmentService().assess(inputs, profile)
    assert assessment.estimated_price.amount == Decimal("0")
    assert assessment.effort.total_hours == 0.0
