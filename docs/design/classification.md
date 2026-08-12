# Classification

Alignment differences become domain-neutral structural operations:
`MATCH`, `INSERT`, `DELETE`, `UPDATE`, `MOVE`, `REORDER` (REQ-061–072).

Classifiers are registered in a **registry**, so a new operation can be added
without changing the matcher or aligner (AC-032).

| Operation | Rule |
|---|---|
| `MATCH` / `UPDATE` | aligned pair; UPDATE when content changed but identity preserved (AC-008) |
| `INSERT` / `DELETE` | target-only / source-only node with **no viable** correspondence; withheld where correspondence is merely unresolved (REQ-058) |
| `MOVE` | confirmed cross-parent match whose confidence clears the move threshold; otherwise degrades to DELETE + INSERT (REQ-070, REQ-071, AC-005) |
| `REORDER` | ordered region whose matched siblings changed relative order; ≥ 2 siblings (REQ-262, AC-006) |

Extended operations (`WRAP`, `UNWRAP`, `SPLIT`, `MERGE`) are modeled but
disabled in the initial release (REQ-072).

## Presence means absence, not uncertainty

`INSERT` and `DELETE` assert that *no viable correspondence exists*. A node that
participates in ambiguous candidates has one that simply cannot be resolved
uniquely, so classifying it as absent would manufacture a precise conclusion out
of an unresolved one. Before emitting a presence operation the classifier asks
two questions (REQ-058):

1. Is this an unresolved position in the [alignment](alignment.md)?
2. Does the node participate in ambiguous candidate edges in the match graph?

Either answer being yes withholds the operation; the ambiguity stays visible in
the match graph and the alignment result. The match-graph check is deliberately
redundant with the aligner's, so an injected aligner that never marks unresolved
positions cannot reintroduce the false positives.

`OperationProfile.unresolved_presence_policy` names the alternatives explicitly:

| Policy | Behavior |
|---|---|
| `SUPPRESS_AMBIGUOUS_NODES` (default) | withhold per node; unambiguous defects in the same region are still reported |
| `SUPPRESS_UNRESOLVED_REGIONS` | withhold for every node in a region holding any unresolved position |
| `EMIT_ALL` | force a total interpretation; forced operations carry the `UNRESOLVED_CORRESPONDENCE_FORCED_BY_POLICY` evidence code |
