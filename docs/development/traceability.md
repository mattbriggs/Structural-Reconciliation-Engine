# Requirement & acceptance traceability

Acceptance criteria are traced directly by test function name — the acceptance
matrix is mechanically greppable:

```bash
grep -rn "def test_ac_0" tests/acceptance
```

## Acceptance coverage (summary)

| Group | Criteria | Where |
|---|---|---|
| Core reconciliation | AC-001..012 | `tests/acceptance/test_ac_core_reconciliation.py` |
| Suppression safety | AC-013..015 | `tests/acceptance/test_ac_suppression.py` |
| Localization | AC-003, 017..024 | `tests/acceptance/test_ac_localization.py` |
| Reporting | AC-025..029 | `tests/acceptance/test_ac_reporting.py` |
| Reviewer decisions | AC-030 | `tests/acceptance/test_ac_reviewer.py` |
| Layering & reuse | AC-031..036 | `tests/contract/`, `tests/unit/adapters/`, `tests/acceptance/test_ac_traceability.py` |
| Repair safety | AC-037..040 | `tests/acceptance/test_ac_localization.py` |
| Pricing independence | AC-035 | `tests/unit/application/test_pricing.py` |

The full per-phase and per-AC status is maintained in the implementation
completion report (`_design/SRE_025-Completion-Report.md`).
