# Determinism

Identical inputs, profiles, configuration, and engine version produce identical
results (REQ-202).

## How it is achieved

- All ordering is derived from **sorted node references** and explicit,
  versioned profile tie-break keys — never from map iteration order, thread
  scheduling, or database retrieval order (REQ-203, REQ-204).
- Results expose `deterministic_fingerprint()`, which excludes volatile timing
  so repeated runs can be compared for semantic stability (AC-012).

## How it is verified

- `tests/acceptance/test_ac_core_reconciliation.py::test_ac_012_deterministic_output`
  reconciles the same inputs twice and compares fingerprints.
- Property tests (`tests/property/test_invariants.py`) assert determinism and
  **node-map iteration-order invariance** over generated trees (REQ-203).
- The quality benchmark runs every labeled case twice and reports
  `deterministic_consistency`.
