"""Immutable, strictly-validated core contracts.

Every externally observable core contract derives from :class:`StrictModel`,
which forbids unknown fields and freezes instances. Later pipeline stages
construct *new* result objects via copy/update rather than mutating earlier
records, preserving auditability (REQ-211, REQ-213).
"""

from __future__ import annotations

from reconciliation.core.contracts.base import ExtensibleModel, StrictModel

__all__ = ["ExtensibleModel", "StrictModel"]
