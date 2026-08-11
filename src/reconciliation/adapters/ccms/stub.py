"""In-memory stub CCMS adapter (REQ-188, reference implementation).

A read-only reference adapter used until a production CCMS is selected. It
serves registered objects and can be told to fail specific object ids so
callers can exercise failure isolation (REQ-190). It maps raw repository
metadata through the anti-corruption helper (REQ-187).
"""

from __future__ import annotations

from reconciliation.adapters.ccms.base import map_repository_metadata
from reconciliation.application.ports.ccms import (
    CCMSObject,
    CCMSObjectRef,
    CCMSReadError,
)


class StubCCMSReadAdapter:
    """A configurable in-memory read-only CCMS adapter."""

    def __init__(self) -> None:
        self._objects: dict[tuple[str, str | None], CCMSObject] = {}
        self._failing: set[str] = set()

    def register(
        self,
        object_id: str,
        content: str,
        *,
        revision: str | None = None,
        media_type: str = "application/xml",
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Register an object retrievable by id (and optional revision)."""
        obj = CCMSObject(
            object_id=object_id,
            revision=revision,
            content=content,
            media_type=media_type,
            metadata=map_repository_metadata(metadata or {}),
        )
        self._objects[(object_id, revision)] = obj

    def fail(self, object_id: str) -> None:
        """Configure ``object_id`` to raise :class:`CCMSReadError` on read."""
        self._failing.add(object_id)

    def get_object(self, ref: CCMSObjectRef) -> CCMSObject:
        """Retrieve a registered object, honoring an explicit revision."""
        if ref.object_id in self._failing:
            raise CCMSReadError(
                f"simulated CCMS failure for {ref.object_id!r}", object_id=ref.object_id
            )
        obj = self._objects.get((ref.object_id, ref.revision))
        if obj is None and ref.revision is None:
            # Fall back to any revision registered under the id.
            obj = next(
                (o for (oid, _rev), o in self._objects.items() if oid == ref.object_id),
                None,
            )
        if obj is None:
            raise CCMSReadError(
                f"CCMS object {ref.object_id!r} (revision {ref.revision!r}) not found",
                object_id=ref.object_id,
            )
        return obj
