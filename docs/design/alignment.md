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
