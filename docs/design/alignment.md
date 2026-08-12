# Alignment

The aligner organizes confirmed correspondences into a structurally coherent
relationship, expressed in domain-neutral terms (REQ-052–060).

- The children of **every** confirmed pair are aligned (roots included), so a
  moved subtree is still compared internally — an independent defect within it
  is not missed (AC-014).
- Matched siblings are always aligned; a change in their relative order under an
  **ordered** parent is a reorder, not an insert/delete (REQ-067). Under an
  **unordered** parent, order is ignored (AC-007).
- The longest-common-subsequence utility (`alignment/lcs.py`) is available for
  order-sensitive sequence alignment.

## Three states, not two

The alignment result distinguishes **confirmed correspondence**, **confirmed
absence**, and **unresolved ambiguity** (REQ-058). Collapsing the last two is
what turns one uncertainty into several confident-looking defects.

| Edge kind | Claim |
|---|---|
| `ALIGNED` | a confirmed correspondence holds at this position |
| `SOURCE_ONLY` / `TARGET_ONLY` | no viable correspondence exists for this node |
| `UNRESOLVED_SOURCE` / `UNRESOLVED_TARGET` | a viable correspondence exists but is not uniquely resolvable |

A child with no confirmed match that participates in ambiguous candidate edges
becomes an unresolved position naming those candidates
(`ambiguous_match_ids`). Its parent region is then marked `unresolved` and
listed in `AlignmentResult.unresolved_region_ids`, and the engine emits an
`UNRESOLVED_ALIGNMENT_REGION` diagnostic. Classification must not turn an
unresolved position into `INSERT`/`DELETE` — see
[Classification](classification.md).

Ambiguity is contained, not contagious: marking a region unresolved does not
hide the confidently one-sided nodes beside it, so a real defect next to an
ambiguity is still reported. `OperationProfile.unresolved_presence_policy`
selects between that default (`SUPPRESS_AMBIGUOUS_NODES`), whole-region caution
(`SUPPRESS_UNRESOLVED_REGIONS`), and a forced total interpretation
(`EMIT_ALL`).

Only the `LCS` strategy is implemented. Requesting another one does not silently
fall back: the engine emits an `ALIGNMENT_STRATEGY_NOT_IMPLEMENTED` diagnostic
and applies LCS. Confirmed matches act as structural anchors implicitly, so
`use_anchor_partitioning` is advisory today.
