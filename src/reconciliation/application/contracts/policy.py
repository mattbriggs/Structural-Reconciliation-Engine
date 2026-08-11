"""Locale-variation policy contract (REQ-103-109).

A policy declares which structural differences are *permitted* for a locale so
the interpreter can mark them exempt rather than treating every divergence as
an error (REQ-106). Policies are versioned, immutable, and validated before use
(REQ-108, REQ-109). They never alter the underlying core result (REQ-105).
"""

from __future__ import annotations

from pydantic import Field, model_validator

from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.profiles import OperationType


class LocaleVariationRule(StrictModel):
    """One permitted locale variation (REQ-104).

    :ivar rule_id: Stable, versioned rule identifier.
    :ivar permitted_operation: The structural operation this rule permits
        (e.g. ``INSERT`` permits an extra locale node).
    :ivar node_types: Node types the rule applies to; empty means all types.
    :ivar justification: Human-readable rationale (REQ-104).
    """

    rule_id: str = Field(min_length=1)
    permitted_operation: OperationType
    node_types: frozenset[str] = frozenset()
    justification: str = Field(min_length=1)

    def applies_to(self, operation: OperationType, node_type: str) -> bool:
        """True if this rule permits ``operation`` for ``node_type``."""
        if operation is not self.permitted_operation:
            return False
        return not self.node_types or node_type in self.node_types


class LocaleVariationPolicy(StrictModel):
    """A versioned set of permitted locale variations (REQ-103, REQ-108).

    :ivar policy_id: Stable identifier.
    :ivar version: Policy version recorded for traceability (REQ-283).
    :ivar locale: Locale this policy applies to.
    :ivar confirmed_match_threshold: Confidence at or above which a confirmed
        match is reported ``CONFIRMED_MATCH`` rather than ``PROBABLE_MATCH``.
    :ivar rules: Permitted-variation rules; rule ids must be unique (REQ-109).
    """

    policy_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    locale: str = Field(min_length=1)
    confirmed_match_threshold: float = Field(default=0.9, ge=0.0, le=1.0)
    rules: tuple[LocaleVariationRule, ...] = ()

    @model_validator(mode="after")
    def _unique_rule_ids(self) -> LocaleVariationPolicy:
        ids = [r.rule_id for r in self.rules]
        if len(set(ids)) != len(ids):
            raise ValueError("locale-variation rule ids must be unique (REQ-109)")
        return self
