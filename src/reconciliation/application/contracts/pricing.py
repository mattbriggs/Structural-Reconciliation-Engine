"""Pricing boundary contracts (REQ-157-164, AC-035).

Pricing consumes *measured facts* from the versioned report/summary contract
(REQ-162) and produces *estimated* effort and price, keeping the two clearly
separated (REQ-163). The reconciliation core contains no rates or currency
(REQ-161); all commercial policy lives in a :class:`PricingProfile`. A generated
assessment identifies the pricing profile version and its inputs (REQ-164).

Changing a pricing profile cannot change any reconciliation output — pricing is
a pure consumer (AC-035).
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field, model_validator

from reconciliation.core.contracts.base import StrictModel

#: The node categories pricing can assign effort/price to (mirrors NodeCounts).
PRICING_CATEGORIES: tuple[str, ...] = (
    "confirmed",
    "probable",
    "ambiguous",
    "missing",
    "extra",
    "structurally_divergent",
    "exempt",
)


class Money(StrictModel):
    """A monetary amount in a named currency."""

    amount: Decimal
    currency: str = Field(min_length=1)


class PricingInputMetrics(StrictModel):
    """Measured workload facts consumed by pricing (REQ-157, REQ-163).

    :ivar report_contract_version: Version of the report contract these facts
        came from (REQ-162).
    :ivar job_id: The comparison job.
    Category counts mirror the report's node counts; they are *facts*, never
    estimates.
    """

    report_contract_version: str
    job_id: str
    confirmed: int = 0
    probable: int = 0
    ambiguous: int = 0
    missing: int = 0
    extra: int = 0
    structurally_divergent: int = 0
    exempt: int = 0
    direct_issue_count: int = 0
    suppressed_effect_count: int = 0

    def count_for(self, category: str) -> int:
        """Return the measured count for a pricing category."""
        return int(getattr(self, category, 0))


class CategoryRate(StrictModel):
    """Effort and unit price assigned to one category (REQ-160)."""

    category: str
    effort_hours: float = Field(ge=0.0)
    unit_price: Decimal = Field(ge=0)


class PricingProfile(StrictModel):
    """A versioned commercial pricing profile (REQ-160, REQ-164).

    :ivar profile_id: Stable identifier.
    :ivar version: Profile version recorded in assessments.
    :ivar currency: Currency for all prices in this profile.
    :ivar rates: Per-category effort/price rates; categories must be known.
    """

    profile_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    currency: str = Field(min_length=1)
    rates: tuple[CategoryRate, ...] = ()

    @model_validator(mode="after")
    def _known_unique_categories(self) -> PricingProfile:
        seen: set[str] = set()
        for rate in self.rates:
            if rate.category not in PRICING_CATEGORIES:
                raise ValueError(f"unknown pricing category {rate.category!r}")
            if rate.category in seen:
                raise ValueError(f"duplicate pricing category {rate.category!r}")
            seen.add(rate.category)
        return self


class EffortEstimate(StrictModel):
    """An estimated effort total and per-category breakdown (REQ-163)."""

    total_hours: float = Field(ge=0.0)
    breakdown: dict[str, float] = Field(default_factory=dict)


class PricingAssessment(StrictModel):
    """A pricing assessment: measured facts plus estimated effort and price.

    :ivar pricing_profile_id: The pricing profile used (REQ-164).
    :ivar pricing_profile_version: Its version (REQ-164).
    :ivar inputs: The measured facts the assessment consumed (REQ-163, REQ-164).
    :ivar effort: The estimated effort (clearly an estimate, REQ-163).
    :ivar estimated_price: The calculated price (clearly calculated, REQ-163).
    :ivar price_breakdown: Per-category calculated price.
    """

    pricing_profile_id: str
    pricing_profile_version: str
    inputs: PricingInputMetrics
    effort: EffortEstimate
    estimated_price: Money
    price_breakdown: dict[str, Money] = Field(default_factory=dict)
