"""Document profile registry (REQ-003, REQ-181, REQ-230).

Maps a ``document_profile_id`` to the adapter and typed profile bundle used to
run a comparison. The registry is generic: concrete adapters are *registered*
by the composition root (delivery), keeping the application layer free of
concrete adapter imports.
"""

from __future__ import annotations

from dataclasses import dataclass

from reconciliation.application.ports.adapters import DocumentAdapter
from reconciliation.profiles.contracts import ProfileBundle


@dataclass(frozen=True)
class DocumentProfile:
    """A registered document profile: an adapter plus its profile bundle."""

    adapter: DocumentAdapter
    bundle: ProfileBundle


class DocumentProfileRegistry:
    """Resolves document profile ids to adapters and bundles."""

    def __init__(self) -> None:
        self._profiles: dict[str, DocumentProfile] = {}

    def register(self, profile_id: str, adapter: DocumentAdapter, bundle: ProfileBundle) -> None:
        """Register a document profile under ``profile_id``."""
        self._profiles[profile_id] = DocumentProfile(adapter=adapter, bundle=bundle)

    def resolve(self, profile_id: str) -> DocumentProfile:
        """Return the profile for ``profile_id``.

        :raises KeyError: If the profile id is not registered.
        """
        return self._profiles[profile_id]

    def known_ids(self) -> tuple[str, ...]:
        """Return the registered profile ids in sorted order."""
        return tuple(sorted(self._profiles))
