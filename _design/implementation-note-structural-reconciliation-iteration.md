# Implementation Note: Next Iteration on Structural Reconciliation

Date: August 11, 2026

## Purpose

This iteration should focus on one outcome above all others:

Reduce false-positive structural findings after the first real divergence without
claiming certainty where the engine only has ambiguity.

The previous review showed that the current abstraction is directionally strong,
but there is still a critical semantic failure mode:

- ambiguous correspondence can still degrade into `DELETE` + `INSERT`
- localization interpretation then reports both `AMBIGUOUS_MATCH` and
  `MISSING_IN_LOCALE` / `EXTRA_IN_LOCALE` for the same structural situation

That is exactly the kind of diagnostic noise this engine is supposed to prevent.

## Primary Implementation Goal

Introduce a first-class "unresolved alignment" path and prevent ambiguous
regions from being converted into hard presence defects.

This is the highest-value correction because it is tightly aligned with the
original XML-to-XML comparison problem:

- when identity is uncertain, do not force a structural conclusion
- preserve ambiguity as a reviewable result
- only emit `INSERT` / `DELETE` when the engine has enough confidence to treat
  the node as truly unmatched

## What To Change First

### 1. Stop turning ambiguous nodes into hard missing/extra results

Current behavior is logically inconsistent:

- the core preserves ambiguity in the match graph
- the classifier still emits `DELETE` / `INSERT` for those same nodes
- the application layer reports both ambiguity and presence defects

Target behavior:

- if a source node participates in ambiguous candidates, do not emit `DELETE`
  for it by default
- if a target node participates in ambiguous candidates, do not emit `INSERT`
  for it by default
- unresolved cases should surface as ambiguity, not absence

Practical rule:

- `DELETE` and `INSERT` should mean "no viable correspondence"
- ambiguous candidate presence means "viable correspondence exists, but is not
  uniquely resolvable"

### 2. Add explicit unresolved alignment output

The contracts already suggest this direction:

- `AlignmentResult.unresolved_region_ids`
- `AlignmentProfile.use_anchor_partitioning`
- multiple alignment strategies

But the current aligner does not actually use these concepts.

This iteration should make unresolved alignment real, even in a minimal form.

Suggested minimal implementation:

- detect sibling regions where one or more nodes participate in ambiguous
  candidate edges
- mark that parent region as unresolved
- avoid emitting hard presence operations from unresolved regions unless an
  explicit policy says otherwise

Do not try to solve full tree edit distance here. A clean unresolved path is
more valuable than an overambitious matcher.

### 3. Change localization interpretation so ambiguity suppresses contradictory statuses

In the localization layer, ambiguous correspondence should dominate conflicting
presence statuses.

Target behavior:

- if a source node is part of an ambiguous match group, do not also report
  `MISSING_IN_LOCALE`
- if a target node is part of an ambiguous match group, do not also report
  `EXTRA_IN_LOCALE`

This can be implemented as either:

- preventing those operations in the core, which is cleaner
- filtering contradictory downstream statuses in the application layer, which is
  a useful defense in depth

Best approach for this iteration:

- fix it in the core
- keep a defensive application-layer guard as a second barrier

## Recommended Scope Boundary

Do this now:

- unresolved-region handling
- ambiguity-aware insert/delete suppression
- acceptance tests proving the contradictory-status bug is gone
- packaging cleanup if time permits

Do not do this now:

- full weighted dynamic-programming alignment
- wrap/unwrap/split/merge classification
- heavy repair planning
- broad profile expansion without implementation behind it

The repo already risks exposing more capability in contracts than the runtime
actually honors. This iteration should close that gap, not widen it.

## Proposed Design Direction

### Core semantic distinction

The engine should distinguish three states:

1. Confirmed correspondence
2. Confirmed absence
3. Unresolved ambiguity

Today, states 2 and 3 bleed together.

The fix is not just algorithmic. It is semantic.

### Minimal classifier rule change

Before emitting `DELETE` or `INSERT`, ask:

- does this node participate in ambiguous candidate edges?
- is its parent region unresolved?

If yes, do not emit a hard presence operation.

Instead:

- retain ambiguity in the match/alignment result
- optionally emit a dedicated unresolved diagnostic later if needed

### Minimal aligner rule change

The aligner does not need a major rewrite for this iteration.

It only needs enough logic to:

- identify regions contaminated by ambiguity
- record them as unresolved
- avoid implying a clean structural interpretation where one does not exist

That is enough to improve correctness substantially.

## Suggested Test Additions

Add acceptance tests for these cases:

### A. Repeated sibling ambiguity does not degrade to missing/extra

Source:

- two structurally identical siblings with no stable IDs

Target:

- two structurally identical siblings with no stable IDs

Expected:

- ambiguous match issues only
- no `DELETE`
- no `INSERT`
- no `MISSING_IN_LOCALE`
- no `EXTRA_IN_LOCALE`

### B. Mixed region with one true insert and one ambiguous pair

Source:

- one known stable node
- one ambiguous repeated structure

Target:

- same stable node
- ambiguous repeated structure
- one actual extra node with stable distinguishing evidence

Expected:

- real extra node still reported
- ambiguous nodes remain ambiguous
- ambiguity does not swallow the real defect

### C. Ambiguous moved-like structure stays unresolved below confidence threshold

Source:

- subtree under parent A

Target:

- similar subtree under parent B with insufficient evidence

Expected:

- no confident `MOVE`
- no contradictory `DELETE` + `INSERT` if ambiguity remains plausible
- unresolved or ambiguous result instead

### D. Localization layer does not emit contradictory statuses

Force a case where the core returns ambiguity.

Expected:

- ambiguous localization issue present
- no simultaneous missing/extra issue for the same participating nodes

## Packaging Cleanup

This is secondary, but worth fixing soon.

The current package advertises a CLI on base install even though the CLI depends
on optional runtime layers such as `typer`, and the default composition path
depends on DITA/XML extras.

Clean options:

- move the CLI entry point behind a `cli` extra and document that clearly
- or promote the required CLI/runtime dependencies into the base install

Recommendation:

- if this repo is meant primarily as a reusable core, keep base install small
- make the CLI explicitly extra-backed

That keeps the packaging story honest.

## Success Criteria For This Iteration

Call the iteration successful if all of the following are true:

- ambiguous repeated structures no longer produce contradictory missing/extra
  results
- `DELETE` / `INSERT` mean actual absence, not unresolved ambiguity
- unresolved alignment is represented explicitly somewhere in the result model
- localization output no longer inflates uncertainty into multiple false
  findings
- tests demonstrate the difference with at least one regression case matching
  the original cascade-noise problem

## Short Version

If time is limited, do this in order:

1. Make insert/delete ambiguity-aware
2. Mark unresolved regions explicitly
3. Add regression tests for repeated ambiguous siblings
4. Add application-layer guard against contradictory statuses
5. Clean up packaging

This iteration should optimize for semantic honesty, not sophistication.

If the engine cannot know, it should say "uncertain" and stop, rather than
manufacturing a structurally precise lie.
