"""Separate benchmark and evaluation tooling (SRS §9.7, plan §7).

Calculates reconciliation *quality* (precision/recall, ambiguity, determinism)
against a labeled corpus and captures *performance* records (timing, candidate
counts, peak memory). This tooling is not part of the runtime pipeline; it
consumes the public contracts. It never declares production thresholds
"validated" — it only measures and reports (plan §7 "no invented production
threshold").
"""

from __future__ import annotations
