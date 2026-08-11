"""Infrastructure adapters implementing application ports (REQ-250).

Persistence (SQLite) and filesystem artifact storage live here, behind the
ports declared in :mod:`reconciliation.application.ports`. Nothing here is
imported by the core (AC-031); these modules depend only on shared contracts.
"""

from __future__ import annotations
