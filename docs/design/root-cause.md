# Root-cause analysis

The analyzer distinguishes **root** operations from **derived** effects and can
retain multiple candidate explanations when none dominates (REQ-073–080).

- The explanatory objective balances edit cost against confidence-weighted
  plausibility — it does **not** minimize operation count alone (REQ-074).
- Ambiguity in the match graph is surfaced as an ambiguous causal graph, so an
  ambiguous relationship is never silently converted into a repairable
  conclusion (REQ-080, AC-038).
- The causal graph rejects invalid cycles.

Costs and tie-break rules are profile-tunable; the defaults are illustrative,
not calibrated production values.
