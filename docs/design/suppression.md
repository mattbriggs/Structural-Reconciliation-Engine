# Cascade suppression

Suppression removes **derived** mismatches from the primary issue list while
retaining them for audit (REQ-081–089).

- Suppression fires only when the root operation clears the applicable rule's
  threshold (REQ-081, AC-015).
- Every suppressed effect records its root operation, rule, confidence, and a
  resolved independent-defect check (AC-013).
- An **independent defect** inside a root operation's region (e.g. a content
  change on a node within a moved subtree) is **retained**, not suppressed
  (REQ-084, AC-014).
- Suppression never deletes the underlying diagnostic record (REQ-267).

The HTML report shows the suppression count and lets a reviewer reveal the
suppressed records (AC-016).
