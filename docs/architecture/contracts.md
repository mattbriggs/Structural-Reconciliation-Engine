# Contracts

Every externally observable contract derives from a strict base model
(`extra="forbid"`, `frozen=True`), so records are immutable and reject unknown
fields. Later pipeline stages construct **new** result objects rather than
mutating earlier ones, preserving auditability.

## Core contracts

| Contract | Key invariants |
|---|---|
| `CanonicalTree` / `CanonicalNode` | rooted, acyclic, resolvable refs, unique containment (REQ-165–170) |
| `MatchingProfile` / `AlignmentProfile` / `OperationProfile` / `SuppressionProfile` | known features; thresholds in `[0,1]`; deterministic tie-break |
| `MatchCandidate` / `MatchGraph` | confirmed one-to-one; evidence required for confirmed/ambiguous (REQ-254–258) |
| `StructuralOperation` | operation-specific invariants (REORDER ≥ 2 siblings; MOVE changes parent) |
| `CausalOperationGraph` | valid refs; no invalid causal cycle |
| `SuppressedEffect` | existing root operation; resolved independent-defect check |
| `ReconciliationResult` | contract version; deterministic ordering; completeness flag |

## Confidence

Feature **score** and calibrated **confidence** are distinct throughout
(REQ-046). Uncalibrated values are labeled scores, never probabilities
(REQ-277, REQ-278). See [Confidence](../design/confidence.md).

## API reference

The full, docstring-driven contract reference is on the
[Python API](../api/python.md) page.
