"""Summary renderer (REQ-156-159).

Renders the localization summary — counts and rates by status, operation,
recommended action, and node category, plus direct vs suppressed counts — as a
typed JSON document suitable for dashboards and pricing/effort inputs.
"""

from __future__ import annotations

import json

from reconciliation.application.contracts.localization import LocalizationValidationResult


class SummaryRenderer:
    """Renders the localization summary to typed JSON."""

    media_type = "application/json"

    def render(self, result: LocalizationValidationResult) -> str:
        """Render the summary counts to a JSON string.

        :param result: The localization validation result.
        :returns: A JSON string of summary counts and rates.
        """
        summary = result.summary
        total = summary.direct_issue_count or 1
        payload = {
            "job_id": result.job_id,
            "locale": result.locale,
            "status_counts": summary.status_counts,
            "operation_counts": summary.operation_counts,
            "action_counts": summary.action_counts,
            "node_counts": summary.node_counts.model_dump(mode="json"),
            "direct_issue_count": summary.direct_issue_count,
            "suppressed_effect_count": summary.suppressed_effect_count,
            "rates": {
                status: round(count / total, 6)
                for status, count in summary.status_counts.items()
            },
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)
