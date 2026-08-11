# Testing

```bash
pytest
pytest --cov=src/reconciliation --cov-branch --cov-report=term-missing
ruff check src tests
mypy src
```

## Test taxonomy

| Suite | Location | Purpose |
|---|---|---|
| Unit | `tests/unit/` | services, validators, scorers, renderers in isolation |
| Contract | `tests/contract/` | core-independence boundary (AC-031) |
| Property | `tests/property/` | invariants + determinism over generated trees |
| Acceptance | `tests/acceptance/` | AC-001..AC-040 traceability (`test_ac_0*`) |
| Security | `tests/security/` | XXE, entity expansion, depth limits |
| Integration | `tests/integration/` | DITA → canonical → engine → localization |
| Performance | `tests/performance/` | wide/deep/repetitive/high-edit |
| Benchmark | `tests/benchmark/` | precision/recall on the labeled corpus |

## Coverage targets

Core ≥ 95% line / 90% branch; application ≥ 90%; adapters/reporting/delivery
≥ 85%; project ≥ 90% line. CI enforces `fail_under = 90`.
