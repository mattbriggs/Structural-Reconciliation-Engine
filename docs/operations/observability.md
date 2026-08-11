# Observability

Structured logging uses `structlog` (REQ-243–246).

## Correlation & redaction

- A correlation id is bound via context vars and propagated into every event
  within the context (REQ-245).
- A redaction processor **always** masks credential-like keys (REQ-220) and, by
  default, content-bearing keys (REQ-221). The masking logic is a pure function
  (`redact_mapping`) and is unit-tested.

## Metrics

`build_observability_report` derives counts and timings from a job outcome:
nodes, candidates, matches, ambiguities, operations, suppressions,
recommendations, and per-stage durations (REQ-244).

Critically, it distinguishes a **technical failure** from a **completed
comparison that merely contains validation issues** (REQ-246): `technical_failure`
vs `completed_with_issues`.

When a logger is configured, `ComparisonJobService` emits redaction-safe
`comparison.stage` and `comparison.outcome` events — never content.
