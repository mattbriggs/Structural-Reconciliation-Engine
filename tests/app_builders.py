"""Test helpers for the localization application layer.

Kept separate from :mod:`tests.builders` (which is deliberately core-only) so
the core independence boundary stays visible: these helpers import the
application layer, core tests do not.
"""

from __future__ import annotations

from reconciliation.application.contracts.common import AuthoritativeSide
from reconciliation.application.contracts.localization import LocalizationValidationResult
from reconciliation.application.contracts.policy import LocaleVariationPolicy
from reconciliation.application.services.localization_validation import (
    LocalizationValidationService,
)
from reconciliation.core.contracts.tree import CanonicalTree
from tests.builders import reconcile


def localize(
    source: CanonicalTree,
    target: CanonicalTree,
    *,
    locale: str = "fr-FR",
    authoritative_side: AuthoritativeSide = AuthoritativeSide.SOURCE,
    policy: LocaleVariationPolicy | None = None,
    **reconcile_kwargs: object,
) -> LocalizationValidationResult:
    """Reconcile two trees and interpret the result into localization terms."""
    result = reconcile(source, target, **reconcile_kwargs)  # type: ignore[arg-type]
    return LocalizationValidationService().validate(
        result,
        source,
        target,
        locale=locale,
        authoritative_side=authoritative_side,
        policy=policy,
    )


def statuses(result: LocalizationValidationResult) -> list[str]:
    """Return the localization status names present in a result."""
    return [issue.localization_status.value for issue in result.issues]


def issue_with_status(result: LocalizationValidationResult, status: str):
    """Return the first issue with the given status name, or ``None``."""
    for issue in result.issues:
        if issue.localization_status.value == status:
            return issue
    return None
