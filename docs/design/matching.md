# Matching

The matcher produces a **match graph** rather than committing every node to one
correspondence, preserving ambiguity and uncertainty.

## Strategy (REQ-037–051)

1. **Authoritative identifiers.** A persistent id that is unique and
   non-duplicated in *both* trees, on type-compatible nodes, yields a confirmed
   match independent of lexical similarity. Duplicated ids are never treated as
   authoritative (AC-010).
2. **Similarity.** Remaining nodes are scored pairwise from independent
   evidence (semantic signature, normalized label, child signature). Hard
   constraints (node-type incompatibility) disqualify candidates (AC-011).
   Ambiguity within the configured margin is preserved rather than resolved by
   position (AC-009). Below-threshold pairs are left unmatched (AC-005).

## Applicability-normalized scoring

A feature contributes to the score's denominator only when its signal is
*present*. An absent id or label therefore does not penalize a node that was
never expected to carry one — the key to keeping id-less repeated structures
ambiguous rather than unmatched.

## Score vs confidence

The weighted feature **score** summarizes evidence; the **confidence** is the
(possibly calibrated) belief derived from it. An authoritative id establishes
identity with maximal confidence, distinct from the diluted score, so a
content or structural change on an authoritatively-identified node does not
weaken the match (AC-008, AC-024).
