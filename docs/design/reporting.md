# Reporting

Renderers consume the immutable `LocalizationValidationResult` and never alter
conclusions (REQ-252).

| Renderer | Output | Notes |
|---|---|---|
| JSON | typed document | confidence as numbers, flags as Booleans, evidence arrays (AC-028) |
| CSV | UTF-8 rows | all applicable columns; `;`-joined lists (AC-027) |
| Summary | counts/rates | by status, operation, action, node category (REQ-156–159) |
| HTML | self-contained page | embedded CSS/JS, no network (REQ-146) |

The flattened `ReportTable` carries stable ids so rows link across formats
(AC-029). Reviewer decisions can be surfaced in the `reviewer_decision` column
while the engine's original conclusion is retained (AC-030).

## Accessibility (REQ-237–242)

Semantic landmarks, scoped table headers, keyboard-operable filters, status
conveyed by text **and** symbol (not color alone), textual confidence
interpretation, and an explicit "human review required" flag for ambiguous
findings.
