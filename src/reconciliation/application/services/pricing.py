"""Pricing assessment service (REQ-160-164, AC-035).

Builds measured :class:`PricingInputMetrics` from the versioned localization
summary (REQ-162) and calculates effort and price under a
:class:`PricingProfile`. This service is a pure consumer: it never references
the reconciliation engine or mutates any result, so changing pricing cannot
change reconciliation output (AC-035).
"""

from __future__ import annotations

from decimal import Decimal

from reconciliation.application.contracts.localization import LocalizationValidationResult
from reconciliation.application.contracts.pricing import (
    EffortEstimate,
    Money,
    PricingAssessment,
    PricingInputMetrics,
    PricingProfile,
)


def build_pricing_inputs(result: LocalizationValidationResult) -> PricingInputMetrics:
    """Derive measured pricing inputs from a localization result's summary.

    Consumes only the versioned summary/report contract, never engine internals
    (REQ-162).

    :param result: The localization validation result.
    :returns: Measured :class:`PricingInputMetrics`.
    """
    counts = result.summary.node_counts
    return PricingInputMetrics(
        report_contract_version=result.contract_version,
        job_id=result.job_id,
        confirmed=counts.confirmed,
        probable=counts.probable,
        ambiguous=counts.ambiguous,
        missing=counts.missing,
        extra=counts.extra,
        structurally_divergent=counts.structurally_divergent,
        exempt=counts.exempt,
        direct_issue_count=result.summary.direct_issue_count,
        suppressed_effect_count=result.summary.suppressed_effect_count,
    )


class PricingAssessmentService:
    """Calculates effort and price from measured metrics and a pricing profile."""

    def assess(
        self, inputs: PricingInputMetrics, profile: PricingProfile
    ) -> PricingAssessment:
        """Calculate a pricing assessment.

        :param inputs: The measured workload facts.
        :param profile: The commercial pricing profile.
        :returns: A :class:`PricingAssessment` separating facts from estimates.
        """
        total_hours = 0.0
        total_price = Decimal(0)
        effort_breakdown: dict[str, float] = {}
        price_breakdown: dict[str, Money] = {}

        for rate in profile.rates:
            count = inputs.count_for(rate.category)
            if count == 0:
                continue
            hours = round(count * rate.effort_hours, 6)
            price = rate.unit_price * count
            total_hours += hours
            total_price += price
            effort_breakdown[rate.category] = hours
            price_breakdown[rate.category] = Money(amount=price, currency=profile.currency)

        return PricingAssessment(
            pricing_profile_id=profile.profile_id,
            pricing_profile_version=profile.version,
            inputs=inputs,
            effort=EffortEstimate(
                total_hours=round(total_hours, 6), breakdown=effort_breakdown
            ),
            estimated_price=Money(amount=total_price, currency=profile.currency),
            price_breakdown=price_breakdown,
        )
