"""CCMS adapters (anti-corruption layer, REQ-186, REQ-190).

Translate CCMS-specific object models into the neutral read DTOs declared by
:mod:`reconciliation.application.ports.ccms`. A reference stub adapter is
provided until a production CCMS is selected (an open question, SRS §10).
"""

from __future__ import annotations
