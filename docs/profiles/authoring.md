# Authoring profiles

A **profile bundle** groups the five typed core profiles a comparison needs:
normalization, matching, alignment, operation, and suppression. Bundles are
version-controlled YAML artifacts loaded into the typed contracts, validated on
load (REQ-024, REQ-280–283).

## Structure

```yaml
bundle_id: my-profile
version: v1
normalization: { profile_id: ..., version: v1, ... }
matching:      { profile_id: ..., version: v1, evidence_priority: [...], ... }
alignment:     { profile_id: ..., version: v1, strategy: LCS, ... }
operation:     { profile_id: ..., version: v1, enabled_operations: [...] }
suppression:   { profile_id: ..., version: v1, rules: [...] }
```

Load a packaged bundle:

```python
from reconciliation.profiles import load_named_bundle
bundle = load_named_bundle("dita_map_v1")
bundle.validate_consistency()
```

Packaged bundles:

| Bundle | Purpose |
|---|---|
| `dita_map_v1` | Source-to-locale DITA map comparison |
| `generic_xml_v1` | Generic XML comparison |
| `generic_json_v1` | Generic JSON data-tree comparison |
| `generic_yaml_v1` | Generic YAML data-tree comparison |

JSON and YAML adapters use shared `data:*` node types. Their generic profiles
make `data:object` children unordered and `data:array` children ordered.

## What a profile controls

- Which properties are identity/content/structure-bearing and how they are
  normalized.
- Evidence priority, feature weights, thresholds, and the ambiguity margin.
- Sibling-order semantics per node type.
- Enabled operations and per-operation thresholds.
- Whether unresolved correspondence may be reported as a presence defect
  (`operation.unresolved_presence_policy`; see
  [Classification](../design/classification.md)).
- Suppression rules and their thresholds.

Profiles configure core behavior but never execute arbitrary infrastructure
code (REQ-253).
