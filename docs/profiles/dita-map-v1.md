# DITA map v1 reference profile

`dita-map-v1` is the reference profile bundle for source-to-locale DITA **map**
comparison. Scope is elements, attributes, references, and metadata — not full
DITA key/conref graph expansion (an open question).

## Identity

The DITA adapter resolves a canonical identity from locale-stable signals in
priority order **`@id` › `@keys` › `@href`** and exposes it as the canonical
`id`, so persistent-identifier matching works across source and locale without
depending on translated navigation titles (REQ-113). Translated `navtitle`s are
carried as content, never as authoritative identity (AC-024).

## Tuning highlights

- `hard_constraint_node_type: true` — differing node types are incompatible.
- `move_confidence_threshold: 0.75`.
- `reltable` node types are unordered.
- Suppression rules cover insert/delete downstream position, move descendant
  path, and reorder position.

See `src/reconciliation/profiles/dita_map_v1.yaml` for the full artifact.
