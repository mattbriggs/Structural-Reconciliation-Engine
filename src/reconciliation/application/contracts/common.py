"""Shared application-contract value types."""

from __future__ import annotations

from enum import Enum


class AuthoritativeSide(str, Enum):
    """Which tree is authoritative for interpretation and repair (REQ-008)."""

    SOURCE = "SOURCE"
    LOCALE = "LOCALE"
