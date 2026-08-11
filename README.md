# Structural Reconciliation Engine

Structural Reconciliation Engine is a confidence-aware Python core for comparing
hierarchical semantic trees. It establishes logical node correspondence before
diagnosing structural differences, so a single insert, delete, move, or reorder
does not explode into a cascade of misleading positional mismatches.

The first product target is source-to-locale XML validation for CCMS
localization workflows, but the reusable core is deliberately domain neutral.
Raw XML, DITA rules, CCMS access, reporting, persistence, and delivery concerns
belong in adapter or application layers above `reconciliation.core`.

## Current Status

This checkout currently contains the reusable in-memory reconciliation core:

- typed canonical tree, profile, command, result, evidence, match, alignment,
  operation, causality, suppression, diagnostic, and metric contracts
- a pure synchronous `DefaultReconciliationEngine`
- deterministic pipeline stages:
  `normalize -> evidence -> match -> align -> classify -> root-cause -> suppress`
- validators for tree and profile invariants
- unit and contract tests for the core boundary1

The project metadata already declares optional extras for XML, API, CLI,
reporting, persistence, YAML, docs, and dev tooling. Those delivery layers are
not present in this repository snapshot yet, so the supported public surface is
the `reconciliation.core` package.

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
imports no XML, DITA, localization, web, persistence, reporting, or CCMS
dependencies.

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
- `OperationProfile`: enabled structural operation vocabulary and thresholds
- `SuppressionProfile`: cascade suppression rules
- `ReconciliationResult`: match graph, alignment, operations, causality,
  suppression, diagnostics, metrics, and exact profile versions

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

Install optional extras only when working on those layers:

```bash
python -m pip install -e ".[xml]"
python -m pip install -e ".[api]"
python -m pip install -e ".[reporting]"
python -m pip install -e ".[all]"
```

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
  version.py          package and contract version manifest

tests/
  contract/           architectural boundary tests
  unit/               contract and core behavior tests
  builders.py         test-only canonical tree/profile builders

_design/
  srs-025-SRS.md
  SRE_025-Implementation-plan.md
```

## Design Documents

The design material in `_design/` is the source of the current requirements and
implementation plan:

- `_design/srs-025-SRS.md`
- `_design/SRE_025-Implementation-plan.md`

Use those documents when extending the operation vocabulary, adding adapters, or
building delivery/reporting layers so the domain-neutral core boundary remains
intact.
