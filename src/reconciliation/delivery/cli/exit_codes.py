"""CLI exit-code policy (REQ-183, REQ-184).

Exit-code semantics are a *configuration model*, not a single hard-coded
definition of "validation failure". The policy separates technical failures
(invalid input, engine error) from detected content findings so callers can
choose how findings affect the exit status.
"""

from __future__ import annotations

from reconciliation.application.contracts.jobs import ComparisonState, JobRecord
from reconciliation.application.contracts.localization import LocalizationValidationResult
from reconciliation.core.contracts.base import StrictModel
from reconciliation.core.contracts.diagnostics import Severity


class ExitCodePolicy(StrictModel):
    """Configurable mapping from outcome to process exit code.

    :ivar success: Code when the comparison completed with no blocking findings.
    :ivar technical_error: Code for invalid input or engine failure (REQ-183).
    :ivar content_findings: Code when findings are treated as a failure.
    :ivar findings_severity: Minimum severity that counts as a blocking finding.
    :ivar treat_findings_as_failure: When False, findings do not change the exit
        code (report-only mode).
    """

    success: int = 0
    technical_error: int = 1
    content_findings: int = 2
    findings_severity: Severity = Severity.ERROR
    treat_findings_as_failure: bool = True


_SEVERITY_ORDER = {Severity.INFO: 0, Severity.WARNING: 1, Severity.ERROR: 2}


def has_blocking_findings(
    result: LocalizationValidationResult, policy: ExitCodePolicy
) -> bool:
    """Return True if any issue meets or exceeds the policy's finding severity."""
    threshold = _SEVERITY_ORDER[policy.findings_severity]
    return any(_SEVERITY_ORDER[issue.severity] >= threshold for issue in result.issues)


def resolve_exit_code(
    record: JobRecord,
    result: LocalizationValidationResult | None,
    policy: ExitCodePolicy,
) -> int:
    """Resolve the process exit code from a job outcome (REQ-183, REQ-184).

    :param record: The job lifecycle record.
    :param result: The localization result when completed.
    :param policy: The exit-code policy.
    :returns: The exit code.
    """
    if record.state is not ComparisonState.COMPLETED or result is None:
        return policy.technical_error
    if policy.treat_findings_as_failure and has_blocking_findings(result, policy):
        return policy.content_findings
    return policy.success
