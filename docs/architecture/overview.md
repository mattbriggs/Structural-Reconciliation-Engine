# Architecture overview

The system is a Python **modular monolith** with a pure, synchronous
reconciliation kernel and replaceable delivery/infrastructure adapters.

```mermaid
flowchart TB
    DELIVERY[Delivery: CLI / FastAPI] --> APP[Application]
    APP --> CORE[Pure reconciliation core]
    APP --> PORTS[Application ports]
    APP --> PROFILE[Typed profiles]
    XML[XML / DITA adapters] -. implements .-> PORTS
    DB[SQLite persistence] -. implements .-> PORTS
    REPORT[Renderers] -. implements .-> PORTS
    CCMS[CCMS adapter] -. implements .-> PORTS
    CORE -. no dependency .-> APP
```

## The pipeline

The core runs a fixed, deterministic pipeline:

```mermaid
flowchart LR
    N[Normalize] --> E[Evidence] --> M[Match] --> A[Align]
    A --> C[Classify] --> R[Root-cause] --> S[Suppress] --> OUT[Result]
```

Each stage boundary is an explicit immutable Pydantic contract. See
[Contracts](contracts.md).

## Layers

| Layer | Responsibility |
|---|---|
| `core` | Domain-neutral reconciliation (no I/O, no framework) |
| `adapters` | XML/DITA/CCMS → `CanonicalTree` (anti-corruption) |
| `application` | Localization interpretation, policy, recommendations, orchestration |
| `reporting` | JSON/CSV/summary/HTML renderers |
| `infrastructure` | SQLite persistence, artifact store, job executors, logging |
| `delivery` | CLI and FastAPI composition roots |

See [Layers & dependency rules](layers.md).
