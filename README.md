# Structural Reconciliation Engine

Structural Reconciliation Engine is a confidence-aware Python toolkit for
comparing hierarchical semantic trees. It establishes logical node
correspondence before diagnosing structural differences, so a single insert,
delete, move, or reorder does not explode into a cascade of misleading
positional mismatches.

The reusable core is deliberately domain neutral. Raw XML, JSON, YAML, DITA
rules, reporting, persistence, and delivery concerns belong in adapter or
application layers above `reconciliation.core`.

## Current Status

This checkout contains a reusable in-memory reconciliation core plus the first
end-to-end XML/DITA localization workflow:

- typed canonical tree, profile, command, result, evidence, match, alignment,
  operation, causality, suppression, diagnostic, and metric contracts
- a pure synchronous `DefaultReconciliationEngine`
- deterministic pipeline stages:
  `normalize -> evidence -> match -> align -> classify -> root-cause -> suppress`
- validators for tree and profile invariants
- hardened XML parsing, generic XML-to-canonical adaptation, generic JSON/YAML
  data-tree adapters, and a DITA map adapter
- YAML-backed profile bundle loading plus packaged `dita-map-v1`,
  `generic-xml-v1`, `generic-json-v1`, and `generic-yaml-v1` profiles
- application orchestration, localization interpretation, reviewer decisions,
  report generation, persistence ports/SQLite implementation, CLI, and FastAPI
  delivery
- unit, contract, integration, acceptance, property, security, performance, and
  benchmark tests

The default document profile remains `dita-map-v1` because the first delivery
workflow is source-to-locale XML validation. Generic XML, JSON, and YAML
profiles are also registered and selectable by profile id.

## Supported Input Shapes

The core is tree-format agnostic: callers can build `CanonicalTree` objects
from any rooted tree-like source and pass them directly to
`reconciliation.core.DefaultReconciliationEngine`.

Out-of-the-box document input support is narrower:

| Input | Current support |
|---|---|
| Canonical trees | Supported directly by the core |
| DITA map XML | Supported end-to-end through `dita-map-v1` |
| Generic XML | Supported through `generic-xml-v1` |
| JSON documents | Supported through `generic-json-v1` |
| YAML documents | Supported through `generic-yaml-v1` |
| YAML profile files | Supported for profile bundles |

So, yes: the tool supports agnostic tree mapping. The core reconciles canonical
trees, while the built-in adapters now map XML, JSON, and YAML syntax into that
shared tree contract. JSON and YAML use shared `data:*` node types, with object
or mapping order ignored by profile and array or sequence order preserved.

## Why It Exists

Traditional tree comparisons often align nodes by sibling position. After a
structural edit, downstream nodes can be paired with the wrong counterparts,
creating false missing, extra, or mismatched reports.

This engine treats identity, content, hierarchy, order, and structural shape as
separate dimensions. It first infers node correspondence, then classifies the
structural operations that explain the observed differences, identifies likely
root causes, and keeps derived effects auditable through suppression results.

## Architecture

The core consumes canonical trees and typed profiles. It performs no I/O and
imports no XML, JSON, YAML, DITA, localization, web, persistence, reporting, or
delivery dependencies.

```text
domain adapter
    -> CanonicalTree + profiles
        -> reconciliation.core.DefaultReconciliationEngine
            -> ReconciliationResult
                -> report, table, API, review workflow, or correction planner
```

Key contracts:

- `CanonicalTree`: immutable rooted tree with stable per-tree node references
- `ReconcileTreesCommand`: source tree, target tree, profiles, and execution
  context
- `MatchingProfile`: identity evidence priority, thresholds, constraints, and
  calibration metadata
- `AlignmentProfile`: sibling-order semantics and alignment strategy
- `OperationProfile`: enabled structural operation vocabulary, thresholds, and
  whether unresolved correspondence may be reported as a presence defect
- `SuppressionProfile`: cascade suppression rules
- `ReconciliationResult`: match graph, alignment, operations, causality,
  suppression, diagnostics, metrics, and exact profile versions

The result keeps three states apart: confirmed correspondence, confirmed
absence, and unresolved ambiguity. `INSERT` and `DELETE` mean "no viable
correspondence exists", so a node whose correspondence is viable but not
uniquely resolvable is held as an unresolved alignment position instead of being
reported as missing or extra. If the engine cannot know, it says uncertain.

## Requirements

- Python `>=3.12`
- Runtime dependencies:
  - `pydantic`
  - `pydantic-settings`
  - `structlog`
  - `typing-extensions`

## Installation

For local development:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

The base install is the reusable core only. Install optional extras when working
on those layers:

```bash
python -m pip install -e ".[xml]"        # XML/DITA adapters
python -m pip install -e ".[cli]"        # reconcile-localization console script
python -m pip install -e ".[api]"        # HTTP API
python -m pip install -e ".[reporting]"  # HTML report renderer
python -m pip install -e ".[all]"        # everything
```

The `reconcile-localization` console script requires the `cli` extra, which
carries typer plus the XML/DITA parser, YAML profile loader, and HTML renderer
its default document-profile path composes. Run without that extra, the script
exits with one line naming the missing dependency.

## Usage

```python
from reconciliation.core.contracts.commands import ExecutionContext, ReconcileTreesCommand
from reconciliation.core.contracts.profiles import (
    AlignmentProfile,
    EvidenceType,
    FeatureWeight,
    MatchingProfile,
    NormalizationProfile,
    OperationProfile,
    SuppressionProfile,
)
from reconciliation.core.contracts.tree import CanonicalNode, CanonicalTree
from reconciliation.core.engine import DefaultReconciliationEngine
from reconciliation.version import CANONICAL_TREE_CONTRACT_VERSION


def tree(tree_id: str, child_ids: list[str]) -> CanonicalTree:
    nodes = {
        "root": CanonicalNode(
            node_ref="root",
            node_type="map",
            child_refs=tuple(child_ids),
        )
    }
    for child_id in child_ids:
        nodes[child_id] = CanonicalNode(
            node_ref=child_id,
            node_type="topicref",
            parent_ref="root",
            identity_properties={"id": child_id},
        )

    return CanonicalTree(
        contract_version=CANONICAL_TREE_CONTRACT_VERSION,
        tree_id=tree_id,
        root_node_ref="root",
        nodes=nodes,
    )


command = ReconcileTreesCommand(
    source_tree=tree("source", ["intro", "setup", "publish"]),
    target_tree=tree("target", ["intro", "publish", "setup"]),
    normalization_profile=NormalizationProfile(profile_id="norm", version="v1"),
    matching_profile=MatchingProfile(
        profile_id="match",
        version="v1",
        evidence_priority=(EvidenceType.PERSISTENT_ID, EvidenceType.NODE_TYPE),
        feature_weights=(
            FeatureWeight(feature=EvidenceType.PERSISTENT_ID, weight=1.0),
        ),
        authoritative_id_features=frozenset({EvidenceType.PERSISTENT_ID}),
        match_threshold=0.6,
        probable_threshold=0.4,
        ambiguity_margin=0.05,
    ),
    alignment_profile=AlignmentProfile(profile_id="align", version="v1"),
    operation_profile=OperationProfile(profile_id="ops", version="v1"),
    suppression_profile=SuppressionProfile(profile_id="suppress", version="v1"),
    execution_context=ExecutionContext(job_id="example"),
)

result = DefaultReconciliationEngine().reconcile(command)

print(result.complete)
print([operation.type.value for operation in result.operations.operations])
```

Expected operation output for this example includes three confirmed matches and
a `REORDER` operation.

## Development

Run the test suite:

```bash
python -m pytest
```

Run linting and type checking:

```bash
python -m ruff check src tests
python -m mypy
```

The core independence contract is important: importing or exercising
`reconciliation.core` must not pull in optional delivery dependencies such as
`lxml`, `fastapi`, `sqlalchemy`, `jinja2`, or domain/application packages.

## Repository Layout

```text
src/reconciliation/
  adapters/
    data_tree/        shared JSON/YAML parsed-data canonicalizer
    json/             generic JSON parser and document adapter
    xml/              hardened XML parser and generic XML adapter
    yaml/             generic YAML parser and document adapter
    dita/             DITA map adapter and identity normalization
  application/
    orchestration/    comparison job service and profile registry
    services/         localization, policy, recommendations, reviewer decisions
    ports/            adapter, repository, artifact, and job ports
  core/
    alignment/        sibling sequence alignment
    causality/        root-cause explanation graph
    classification/   structural operation classifiers
    contracts/        typed public core contracts
    evidence/         identity evidence extraction
    matching/         candidate scoring and match graph construction
    metrics/          stage timing and resource-limit metrics
    normalization/    canonical tree normalization
    suppression/      cascade suppression
    validation/       tree and profile validation
  delivery/
    api/              FastAPI app and routers
    cli/              reconcile-localization command
  infrastructure/
    persistence/      SQLite repositories
    jobs/             in-memory job execution
  profiles/           YAML profile bundle contracts and packaged profiles
  reporting/          JSON/CSV/summary/HTML renderers
  version.py          package and contract version manifest

tests/
  acceptance/         SRS acceptance criteria and workflow tests
  benchmark/          quality and report benchmark tests
  contract/           architectural boundary tests
  integration/        adapter-to-engine pipeline tests
  performance/        scalability and resource tests
  property/           invariant/property tests
  security/           parser and hardening tests
  unit/               contract, core, adapter, app, delivery, reporting tests
  builders.py         test-only canonical tree/profile builders

_design/
  srs-025-SRS.md
  SRE_025-Implementation-plan.md
  2026-08-11-Implementation-Note1.md
```

## Design Documents

The design material in `_design/` is the source of the current requirements and
implementation plan:

- `_design/srs-025-SRS.md`
- `_design/SRE_025-Implementation-plan.md`
- `_design/2026-08-11-Implementation-Note1.md`

Use those documents when extending the operation vocabulary, adding adapters, or
building delivery/reporting layers so the domain-neutral core boundary remains
intact.
