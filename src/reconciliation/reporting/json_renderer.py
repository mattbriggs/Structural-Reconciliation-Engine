"""JSON report renderer (REQ-149, REQ-155, AC-028).

Serializes a report table (and optionally the full localization result) to
typed JSON: confidence as numbers, suppression flags as Booleans, and evidence
as arrays (AC-028). Uses Pydantic serialization so numeric/boolean/list/object
typing is preserved (REQ-155).
"""

from __future__ import annotations

import json

from reconciliation.application.contracts.localization import LocalizationValidationResult
from reconciliation.reporting.contracts import ReportTable


class JsonReportRenderer:
    """Renders a report table to a typed JSON document."""

    media_type = "application/json"

    def render(self, table: ReportTable) -> str:
        """Render just the tabular rows to JSON.

        :param table: The report table.
        :returns: A JSON string with a versioned envelope.
        """
        payload = {
            "schema_version": table.schema_version,
            "job_id": table.job_id,
            "rows": [row.model_dump(mode="json") for row in table.rows],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def render_full(
        self, result: LocalizationValidationResult, table: ReportTable
    ) -> str:
        """Render the full localization result plus flattened rows.

        :param result: The localization validation result.
        :param table: The flattened report table.
        :returns: A JSON string containing summary, issues, recommendations,
            suppressed effects, exact versions, and the tabular rows.
        """
        reconciliation = result.reconciliation
        payload = {
            "schema_version": table.schema_version,
            "localization_contract_version": result.contract_version,
            "job_id": result.job_id,
            "locale": result.locale,
            "authoritative_side": result.authoritative_side.value,
            "versions": reconciliation.profile_versions.model_dump(mode="json"),
            "summary": result.summary.model_dump(mode="json"),
            "issues": [issue.model_dump(mode="json") for issue in result.issues],
            "recommendations": [
                rec.model_dump(mode="json") for rec in result.recommendations
            ],
            "suppressed_effects": [
                effect.model_dump(mode="json")
                for effect in reconciliation.suppression.suppressed_effects
            ],
            "rows": [row.model_dump(mode="json") for row in table.rows],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)
