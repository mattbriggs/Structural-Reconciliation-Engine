# Classification

Alignment differences become domain-neutral structural operations:
`MATCH`, `INSERT`, `DELETE`, `UPDATE`, `MOVE`, `REORDER` (REQ-061–072).

Classifiers are registered in a **registry**, so a new operation can be added
without changing the matcher or aligner (AC-032).

| Operation | Rule |
|---|---|
| `MATCH` / `UPDATE` | aligned pair; UPDATE when content changed but identity preserved (AC-008) |
| `INSERT` / `DELETE` | target-only / source-only node with no confirmed correspondence |
| `MOVE` | confirmed cross-parent match whose confidence clears the move threshold; otherwise degrades to DELETE + INSERT (REQ-070, REQ-071, AC-005) |
| `REORDER` | ordered region whose matched siblings changed relative order; ≥ 2 siblings (REQ-262, AC-006) |

Extended operations (`WRAP`, `UNWRAP`, `SPLIT`, `MERGE`) are modeled but
disabled in the initial release (REQ-072).
