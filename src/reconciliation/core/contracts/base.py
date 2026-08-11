"""Base Pydantic models for immutable core contracts.

:class:`StrictModel` is the project base model: it forbids unknown fields
(``extra="forbid"``) and freezes instances (``frozen=True``) so that
cross-layer records cannot be mutated after construction. Use
:class:`ExtensibleModel` only for records that must carry forward-compatible
extension metadata without kernel changes (REQ-014).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Immutable base model for externally observable contracts.

    :cvar model_config:
        Frozen instances, forbidden unknown fields, validated defaults, and
        validation on assignment. Freezing makes instances hashable and safe
        to share across pipeline stages without defensive copying.

    .. note::
       Do not subclass this for records that legitimately need open-ended
       extension metadata; use :class:`ExtensibleModel` instead so schema
       evolution does not force ``extra="forbid"`` rejections.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_default=True,
        validate_assignment=True,
        str_strip_whitespace=False,
        arbitrary_types_allowed=False,
    )


class ExtensibleModel(BaseModel):
    """Immutable base model that tolerates forward-compatible extension data.

    Used for canonical nodes and profile records that may carry adapter- or
    profile-specific metadata the kernel does not interpret (REQ-014,
    REQ-281). Unknown fields are ignored rather than rejected.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        validate_default=True,
    )
