"""Application layer: localization interpretation, policy, and recommendations.

This layer sits above the pure core. It consumes the domain-neutral
:class:`~reconciliation.core.contracts.results.ReconciliationResult` and
translates it into source-to-locale validation statuses, applies locale
variation policy, assesses translation state, and plans (non-executable)
repair recommendations. It references core *IDs* but never mutates core
records (REQ-176, REQ-177). The core never imports this package (AC-031).
"""

from __future__ import annotations
