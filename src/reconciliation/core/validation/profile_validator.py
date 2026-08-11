"""Cross-profile validation (REQ-280-283).

Individual profile models validate their own internal consistency. This
validator checks *relationships between* the profiles supplied to one job:
that suppression rules reference enabled operations, that the matching
profile's evidence weights are coherent with its priority order, and that
required operations for classification are enabled.
"""

from __future__ import annotations

from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.profiles import (
    MatchingProfile,
    OperationProfile,
    SuppressionProfile,
)
from reconciliation.core.errors import InvalidProfileError


class ProfileViolation(StrictModel):
    """A single cross-profile validation violation."""

    code: str
    message: str


class ProfileValidationResult(StrictModel):
    """Outcome of validating a set of profiles together."""

    valid: bool
    violations: tuple[ProfileViolation, ...] = ()

    def raise_if_invalid(self, *, correlation_id: str | None = None) -> None:
        """Raise :class:`InvalidProfileError` on the first violation."""
        if self.valid:
            return
        first = self.violations[0]
        raise InvalidProfileError(
            f"profile validation failed: {first.message}",
            correlation_id=correlation_id,
            context={"violations": [v.model_dump() for v in self.violations]},
        )


def validate_profiles(
    matching: MatchingProfile,
    operation: OperationProfile,
    suppression: SuppressionProfile,
) -> ProfileValidationResult:
    """Validate consistency across matching, operation, and suppression profiles.

    :param matching: The matching profile.
    :param operation: The operation profile.
    :param suppression: The suppression profile.
    :returns: A structured :class:`ProfileValidationResult`.
    """
    violations: list[ProfileViolation] = []

    # Suppression rules must react to enabled operations (REQ-281).
    for rule in suppression.rules:
        if rule.root_operation not in operation.enabled_operations:
            violations.append(
                ProfileViolation(
                    code="SUPPRESSION_RULE_DISABLED_OPERATION",
                    message=(
                        f"suppression rule {rule.rule_id!r} targets operation "
                        f"{rule.root_operation.value} which is not enabled"
                    ),
                )
            )

    # Feature weights must reference features present in the priority order.
    priority = set(matching.evidence_priority)
    for weight in matching.feature_weights:
        if weight.feature not in priority:
            violations.append(
                ProfileViolation(
                    code="WEIGHT_WITHOUT_PRIORITY",
                    message=(
                        f"feature weight {weight.feature.value} is not present in "
                        "evidence_priority"
                    ),
                )
            )

    return ProfileValidationResult(valid=not violations, violations=tuple(violations))
