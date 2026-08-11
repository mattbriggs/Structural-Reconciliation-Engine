"""Locale-variation policy evaluation (REQ-103-109, AC-021).

Evaluates whether a structural finding is permitted by an applicable locale
policy. Evaluation is deterministic (REQ-108) and *marks* a difference exempt
without removing it (REQ-106); the underlying core result is never altered
(REQ-105).
"""

from __future__ import annotations

from reconciliation.application.contracts.policy import LocaleVariationPolicy
from reconciliation.core.contracts.profiles import OperationType


class LocaleVariationPolicyService:
    """Applies a :class:`LocaleVariationPolicy` to structural findings."""

    def exemption_for(
        self,
        policy: LocaleVariationPolicy | None,
        *,
        locale: str,
        operation: OperationType,
        node_type: str,
    ) -> str | None:
        """Return the id of a rule that permits this finding, if any.

        :param policy: The active locale policy, or ``None`` for no policy.
        :param locale: The comparison locale.
        :param operation: The structural operation observed (e.g. ``INSERT``
            for an extra locale node, ``DELETE`` for a missing one).
        :param node_type: The canonical node type involved.
        :returns: The permitting rule id, or ``None`` if not exempt.
        """
        if policy is None or policy.locale != locale:
            return None
        for rule in policy.rules:
            if rule.applies_to(operation, node_type):
                return rule.rule_id
        return None
