"""CCMS-sourced comparison orchestration (REQ-186-190).

Fetches source and locale documents from a read-only CCMS port and runs the
standard comparison pipeline on their content. A CCMS read failure is isolated
as a ``REJECTED`` job with code ``CCMS_READ_FAILED`` — never a structural
comparison result (REQ-190).
"""

from __future__ import annotations

import uuid

from reconciliation.application.contracts.common import AuthoritativeSide
from reconciliation.application.contracts.jobs import (
    ComparisonRequest,
    ComparisonState,
    JobRecord,
)
from reconciliation.application.orchestration.comparison_job import (
    ComparisonJobService,
    JobOutcome,
)
from reconciliation.application.ports.ccms import (
    CCMSObjectRef,
    CCMSReadError,
    CCMSReadPort,
)


class CCMSComparisonService:
    """Runs comparisons whose inputs come from a read-only CCMS.

    :param ccms: The read-only CCMS port.
    :param comparison_service: The underlying comparison pipeline service.
    """

    def __init__(
        self, ccms: CCMSReadPort, comparison_service: ComparisonJobService
    ) -> None:
        self._ccms = ccms
        self._service = comparison_service

    def run_from_refs(
        self,
        source_ref: CCMSObjectRef,
        locale_ref: CCMSObjectRef,
        *,
        locale: str,
        document_profile_id: str,
        authoritative_side: AuthoritativeSide = AuthoritativeSide.SOURCE,
        job_id: str | None = None,
    ) -> JobOutcome:
        """Fetch two CCMS objects and reconcile them.

        :returns: The comparison outcome, or a ``REJECTED`` record with code
            ``CCMS_READ_FAILED`` if either object cannot be read (REQ-190).
        """
        resolved_job_id = job_id or f"job-{uuid.uuid4()}"
        try:
            source = self._ccms.get_object(source_ref)
            target = self._ccms.get_object(locale_ref)
        except CCMSReadError as exc:
            return JobOutcome(
                record=JobRecord(
                    job_id=resolved_job_id,
                    state=ComparisonState.REJECTED,
                    locale=locale,
                    error_code=exc.code,
                    error_message=exc.message,
                    correlation_id=f"corr-{resolved_job_id}",
                ),
                result=None,
            )

        return self._service.run(
            ComparisonRequest(
                source_content=source.content,
                locale_content=target.content,
                locale=locale,
                document_profile_id=document_profile_id,
                authoritative_side=authoritative_side,
                job_id=resolved_job_id,
            )
        )
