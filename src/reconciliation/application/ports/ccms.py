"""Read-only CCMS integration port (REQ-186-190).

CCMS access lives entirely outside the reconciliation core, behind this port
(REQ-186). The initial release is **read-only** (REQ-188); write-back is out of
scope and would require optimistic-concurrency checks (REQ-189). A read failure
raises :class:`CCMSReadError` and must never be surfaced as a structural
comparison result (REQ-190).
"""

from __future__ import annotations

from typing import Protocol

from reconciliation.core.contracts.base import StrictModel


class CCMSReadError(Exception):
    """Retrieving a CCMS object failed.

    Distinct from reconciliation errors so a CCMS retrieval failure is never
    reported as a comparison result (REQ-190).
    """

    code = "CCMS_READ_FAILED"

    def __init__(self, message: str, *, object_id: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.object_id = object_id
        self.retryable = True


class CCMSObjectRef(StrictModel):
    """A reference to a CCMS object.

    :ivar object_id: Repository object identifier.
    :ivar revision: Specific revision; ``None`` requests the latest.
    """

    object_id: str
    revision: str | None = None


class CCMSObject(StrictModel):
    """A retrieved CCMS object and its repository metadata (REQ-187).

    :ivar object_id: Repository object identifier.
    :ivar revision: The revision actually retrieved.
    :ivar content: The document content (e.g. XML).
    :ivar media_type: Content media type.
    :ivar metadata: Repository metadata mapped into a neutral form (REQ-187),
        e.g. translation-unit id or source reference.
    """

    object_id: str
    revision: str | None = None
    content: str
    media_type: str = "application/xml"
    metadata: dict[str, str] = {}  # noqa: RUF012 - Pydantic field default


class CCMSReadPort(Protocol):
    """Read-only access to a Component Content Management System."""

    def get_object(self, ref: CCMSObjectRef) -> CCMSObject:
        """Retrieve a CCMS object.

        :raises CCMSReadError: If the object cannot be retrieved.
        """
        ...
