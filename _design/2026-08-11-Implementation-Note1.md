# Implementation Note: Generalizing Structural Reconciliation To Common Tree Formats

Date: August 11, 2026

## Purpose

Generalize the current Structural Reconciliation Engine from its first DITA/XML
workflow into a reusable comparison tool for common tree-shaped document
formats: XML, JSON, and YAML.

The important architectural point is that the core is already mostly general.
`reconciliation.core` consumes `CanonicalTree` and typed profiles, not raw XML.
This iteration should therefore add format coverage around the core, not push
format-specific behavior into it.

The goal is:

- compare any two documents that can be faithfully represented as rooted,
  ordered or partly unordered trees
- keep syntax parsing and domain interpretation in adapters/profiles
- preserve the existing deterministic core pipeline
- make XML, JSON, and YAML feel like first-class document profiles in delivery
  surfaces

## Repository Review Summary

The repo already has the right extension seams:

- `CanonicalTree` / `CanonicalNode` in
  `src/reconciliation/core/contracts/tree.py` provide a domain-neutral rooted
  tree contract with identity, content, structural, and extension property
  partitions.
- `DocumentAdapter` in
  `src/reconciliation/application/ports/adapters.py` defines the adapter shape:
  raw document content in, validated `CanonicalTree` out.
- `DocumentProfileRegistry` in
  `src/reconciliation/application/orchestration/registry.py` binds a document
  profile id to both an adapter and a `ProfileBundle`.
- `build_default_registry()` in `src/reconciliation/delivery/composition.py`
  is the composition root for default document profiles.
- `GenericXmlAdapter` and `DitaMapAdapter` show the intended layering:
  vocabulary-agnostic syntax mapping first, domain specialization second.
- `ProfileBundle` already loads YAML artifacts for reconciliation behavior.
  That should remain separate from YAML-as-input-document support.

The core independence contract must remain intact. Adding JSON/YAML support
should not make `reconciliation.core` import `json`, `yaml`, `lxml`, delivery,
or adapter packages.

## Primary Design Decision

Treat XML, JSON, and YAML as different source syntaxes that can all produce the
same canonical tree shape.

Do not create parallel reconciliation engines.
Do not add XML/JSON/YAML branches to the matcher, aligner, classifiers, or
suppression logic.

All format-specific behavior belongs in:

- parser modules under `src/reconciliation/adapters/<format>/`
- canonical adapters under `src/reconciliation/adapters/<format>/`
- optional domain adapters layered on top of generic format adapters
- profile bundles under `src/reconciliation/profiles/`
- delivery composition and documentation

## Target Package Shape

Add these modules:

```text
src/reconciliation/adapters/json/
  __init__.py
  parser.py
  canonical_adapter.py
  errors.py

src/reconciliation/adapters/yaml/
  __init__.py
  parser.py
  canonical_adapter.py
  errors.py
```

Add these profile bundles:

```text
src/reconciliation/profiles/generic_xml_v1.yaml
src/reconciliation/profiles/generic_json_v1.yaml
src/reconciliation/profiles/generic_yaml_v1.yaml
```

The current DITA profile should remain:

```text
src/reconciliation/profiles/dita_map_v1.yaml
```

Register the default generic profiles in:

```text
src/reconciliation/delivery/composition.py
```

Recommended profile ids:

- `generic-xml-v1`
- `generic-json-v1`
- `generic-yaml-v1`
- `dita-map-v1`

Keep `dita-map-v1` as the existing default only if the CLI is still explicitly
positioned as localization-oriented. If the CLI is repositioned as a generic
tree comparison tool, rename the command/help text and make the default profile
format-sensitive or explicit.

## Canonical Mapping Rules

All adapters must produce deterministic node refs. Continue the existing
document-order style:

- root: `n`
- first child: `n.0`
- second child: `n.1`
- nested child: `n.1.0`

Never use source object identity, dictionary iteration accidents, randomized
hashing, or parser-specific memory addresses in `node_ref`.

### XML

The existing XML behavior is already the baseline:

- element nodes become canonical nodes
- element local name becomes `node_type`
- child elements become `child_refs`
- attributes become `structural_properties`
- `id` and `xml:id` become identity properties
- text becomes content
- source location records `document_uri`, line, and XPath when available

Implementation work for generic XML is mostly packaging and registration:

- expose `GenericXmlAdapter` through `DocumentAdapter.adapt_document`
- add or reuse a small wrapper that combines `SecureXmlParser` with
  `GenericXmlAdapter`
- add `generic_xml_v1.yaml`
- register `generic-xml-v1`

Do not remove `DitaMapAdapter`. DITA remains a domain-specific XML adapter with
stronger identity rules.

### JSON

JSON has two possible tree interpretations:

1. Model only containers as nodes and keep scalar values as content.
2. Model containers and scalar fields/items as nodes.

Use option 2 for the generic adapter. It gives the reconciliation engine enough
structure to classify inserts, deletes, moves, reorders, and updates at field
or item granularity.

Recommended JSON node types:

| JSON value | `node_type` |
|---|---|
| document root | `data:document` |
| object | `data:object` |
| object member | `data:property` |
| array | `data:array` |
| array item | `data:item` |
| string | `data:string` |
| number | `data:number` |
| boolean | `data:boolean` |
| null | `data:null` |

Recommended object-member mapping:

- create a `data:property` node for each object key
- put the key in `identity_properties["key"]`
- put the key in `structural_properties["key"]`
- attach the value as the property node's single child unless the value is a
  scalar small enough to store directly as content

Recommended array mapping:

- create a `data:array` node for arrays
- create a `data:item` node for each item
- put the original index in `structural_properties["index"]`
- do not use index as identity evidence by default
- preserve sibling order by default

Recommended scalar mapping:

- represent scalar values as leaf nodes
- store the value in `content_properties["value"]`
- optionally store a normalized string form in `content_properties["text"]` if
  useful for existing weighted similarity behavior

For JSON object members, order should be treated as semantically insignificant
by the generic profile. For JSON arrays, order should be significant by
default.

### YAML

YAML should reuse the JSON canonical model after parsing, because YAML mappings,
sequences, and scalars map cleanly to object, array, and scalar concepts.

Use `yaml.safe_load`, not a loader that constructs arbitrary Python objects.

The generic YAML adapter should:

- parse with safe loading only
- reject multiple-document streams in the first iteration unless an explicit
  profile says how to handle them
- reject anchors, aliases, merge keys, tags, and non-core YAML features if they
  cannot be represented deterministically and safely
- normalize mapping keys to strings or reject non-string keys
- preserve source `document_uri`
- use the same shared `data:*` node types as JSON

Use shared data node types, not YAML-specific node types, for the parsed data
model:

- `data:object`
- `data:property`
- `data:array`
- `data:item`
- `data:string`
- `data:number`
- `data:boolean`
- `data:null`

That makes JSON-vs-YAML comparison possible when both files represent the same
logical data.

## Recommended Node Type Strategy

Prefer shared `data:*` node types for generic JSON and YAML.

Keep XML as element-name based because XML element names usually carry document
vocabulary semantics. A fully generic XML profile can still use node type as
hard compatibility evidence.

Suggested generic data node types:

```text
data:document
data:object
data:property
data:array
data:item
data:string
data:number
data:boolean
data:null
```

This lets the same reconciliation profile compare:

- JSON source to JSON target
- YAML source to YAML target
- JSON source to YAML target, if delivery later permits mixed adapters

The current `ComparisonJobService` resolves one `document_profile_id` and uses
the same adapter for source and locale. Mixed-format comparison would require
either:

- separate `source_document_profile_id` and `target_document_profile_id`
- a composite profile that selects adapters by media type or file extension

Do not add mixed-format orchestration in the first pass unless it is needed by a
product workflow.

## Parser Security And Limits

Mirror the XML adapter's security posture for JSON and YAML.

Add parser limit dataclasses:

```python
JsonSecurityLimits(max_bytes=10_000_000, max_depth=100, max_nodes=100_000)
YamlSecurityLimits(max_bytes=10_000_000, max_depth=100, max_nodes=100_000)
```

Enforce:

- byte-size limit before parsing
- maximum nesting depth
- maximum total node count
- deterministic rejection of unsupported constructs
- no network access
- no arbitrary object construction

JSON parser implementation can use the Python standard library `json` module.
YAML parser implementation should use `pyyaml` from the existing `yaml` extra.

If YAML support becomes part of the default composition path, promote
`pyyaml` from optional to base dependency or make the CLI/API profile selection
fail cleanly when the extra is not installed.

## Profile Bundle Instructions

Create generic profile bundles that are intentionally conservative.

### Generic XML Profile

Recommended matching:

- evidence priority:
  - `PERSISTENT_ID`
  - `NODE_TYPE`
  - `CHILD_SIGNATURE`
  - `ANCESTOR_CONTEXT`
  - `WEIGHTED_SIMILARITY`
- authoritative id features:
  - `PERSISTENT_ID`
- hard node type constraint:
  - `true`

Recommended alignment:

- default order semantics:
  - `ORDERED`

### Generic Data Profile For JSON/YAML

Recommended matching:

- evidence priority:
  - `PERSISTENT_ID`
  - `NODE_TYPE`
  - `ANCESTOR_CONTEXT`
  - `CHILD_SIGNATURE`
  - `WEIGHTED_SIMILARITY`
- authoritative id features:
  - leave empty unless a domain adapter promotes specific keys
- hard node type constraint:
  - `true`

Recommended alignment:

- default order semantics:
  - `ORDERED`
- `data:object` children:
  - `UNORDERED`
- `data:property` children:
  - `ORDERED` only if the property value is modeled as a child
- `data:array` children:
  - `ORDERED`

Generic JSON/YAML should not guess that fields named `id`, `name`, `key`, or
`slug` are authoritative persistent IDs in every domain. That is tempting but
will create false confidence. Instead:

- generic adapters should expose field names as identity for property nodes
- domain adapters may promote selected data values into identity properties
- profile docs should show how to create a domain-specific JSON/YAML adapter
  later

## Implementation Steps

### 1. Preserve the core boundary

Before adding adapters, run or inspect:

```bash
python -m pytest tests/contract/test_core_independence.py
```

After implementation, this test must still pass. If it fails, the change has
crossed the wrong boundary.

### 2. Add a generic data tree builder

To avoid duplicating JSON and YAML canonicalization, add a shared internal
builder used by both adapters.

Recommended location:

```text
src/reconciliation/adapters/data_tree/
  __init__.py
  canonical_adapter.py
  errors.py
```

Alternative:

```text
src/reconciliation/adapters/json/canonical_adapter.py
```

with YAML importing it. The `data_tree` package is cleaner if JSON/YAML are
both first-class.

The builder should accept parsed Python values from a safe parser:

```python
JsonLikeValue = dict[str, object] | list[object] | str | int | float | bool | None
```

It should return `CanonicalTree`.

### 3. Implement JSON parsing

Add `SecureJsonParser`:

- converts `str | bytes` to bytes for size checking
- decodes UTF-8
- calls `json.loads`
- maps `json.JSONDecodeError` to an adapter `InputParseError` equivalent
- enforces max depth and node count after parsing

Reuse existing adapter error concepts where possible. The current XML errors
live under `reconciliation.adapters.xml.errors`; if they are intended to be
format-neutral, move or duplicate only after reviewing import impact. A small
shared `reconciliation.adapters.errors` module would be a useful cleanup.

### 4. Implement YAML parsing

Add `SecureYamlParser`:

- checks byte size
- decodes UTF-8
- uses `yaml.safe_load`
- rejects non-string mapping keys
- rejects multiple documents for now
- enforces max depth and node count after parsing
- treats an empty YAML document as `None` or rejects it explicitly; prefer
  accepting it as `data:null` for consistency with JSON

Be explicit in docs that generic YAML support covers core YAML data structures,
not custom YAML object tags.

### 5. Register document profiles

Update `build_default_registry()` to register:

```python
registry.register("generic-xml-v1", GenericXmlDocumentAdapter(), load_named_bundle("generic_xml_v1"))
registry.register("generic-json-v1", JsonDocumentAdapter(), load_named_bundle("generic_json_v1"))
registry.register("generic-yaml-v1", YamlDocumentAdapter(), load_named_bundle("generic_yaml_v1"))
registry.register("dita-map-v1", DitaMapAdapter(), load_named_bundle("dita_map_v1"))
```

If optional dependencies are missing, fail at profile use time with a clear
adapter/configuration error. Do not make importing the core fail because `lxml`
or `yaml` is absent.

### 6. Update delivery language

The CLI currently says "Source-to-locale XML reconciliation." If this tool is
now generic, update the help text to say "tree document reconciliation" or
"structural document reconciliation."

Also consider renaming the console script in a later breaking release:

```text
reconcile-localization -> reconcile-structure
```

For this iteration, keep the old command to avoid breaking users.

### 7. Document extension points

Update:

```text
docs/development/extension-points.md
docs/profiles/authoring.md
docs/api/cli.md
docs/api/http.md
README.md
```

Add one short example each for XML, JSON, and YAML profile selection.

## Test Plan

Add unit tests:

```text
tests/unit/adapters/test_json_adapter.py
tests/unit/adapters/test_yaml_adapter.py
tests/unit/adapters/test_data_tree_adapter.py
```

Required JSON tests:

- object fields become deterministic `data:property` nodes
- array items preserve order
- scalar updates become `UPDATE`, not delete/insert
- object field order does not change semantic alignment under the generic data
  profile
- malformed JSON is rejected with a stable machine code
- depth, byte, and node-count limits are enforced

Required YAML tests:

- mappings and sequences produce the same canonical shape as equivalent JSON
- non-string mapping keys are rejected or normalized by an explicit rule
- custom tags/unsafe constructs are rejected
- empty document behavior is specified
- malformed YAML is rejected with a stable machine code
- depth, byte, and node-count limits are enforced

Add integration tests:

```text
tests/integration/test_generic_json_pipeline.py
tests/integration/test_generic_yaml_pipeline.py
```

Required pipeline tests:

- JSON object field reorder produces no structural defect
- JSON array reorder produces a `REORDER`
- JSON field addition produces one `INSERT`
- YAML mapping reorder produces no structural defect
- YAML sequence reorder produces a `REORDER`
- equivalent JSON and YAML canonicalization produce compatible node types if
  the shared `data:*` strategy is used

Add contract tests:

- importing `reconciliation.core` still does not import adapter dependencies
- registering JSON/YAML profiles does not alter DITA behavior
- unknown document profile ids are still rejected cleanly

## Acceptance Criteria

This iteration is complete when:

- XML, JSON, and YAML document profiles can be selected by profile id
- generic JSON and YAML adapters produce valid `CanonicalTree` instances
- JSON/YAML mappings are order-insensitive by profile, while arrays/sequences
  remain order-sensitive
- DITA behavior and tests are unchanged
- core independence tests still pass
- malformed or unsafe inputs are rejected before canonicalization
- docs clearly explain the difference between syntax adapters and
  reconciliation profiles

## Recommended Scope Boundary

Do this now:

- generic XML registration
- generic JSON adapter
- generic YAML adapter
- shared data-tree canonicalizer for JSON/YAML
- generic profile bundles
- CLI/API profile selection docs
- focused unit, integration, and contract tests

Do not do this now:

- arbitrary mixed-format source/target comparison
- JSON Schema, OpenAPI, AsyncAPI, Kubernetes, or domain-specific YAML identity
  rules
- YAML custom tag interpretation
- streaming/incremental parsing for very large documents
- graph reconciliation for references outside the document tree
- changing the core operation vocabulary

## Short Version

The kernel is already general. Generalize the product by widening the adapter
and profile layer:

1. Keep `CanonicalTree` as the one internal representation.
2. Add generic JSON/YAML parsers with XML-like safety limits.
3. Use shared `data:*` node types for JSON/YAML.
4. Register `generic-xml-v1`, `generic-json-v1`, and `generic-yaml-v1`.
5. Add profile bundles that make mappings unordered and arrays ordered.
6. Prove with tests that the core still does not know or care which syntax
   produced the tree.
