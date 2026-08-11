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

## What a profile controls

- Which properties are identity/content/structure-bearing and how they are
  normalized.
- Evidence priority, feature weights, thresholds, and the ambiguity margin.
- Sibling-order semantics per node type.
- Enabled operations and per-operation thresholds.
- Suppression rules and their thresholds.

Profiles configure core behavior but never execute arbitrary infrastructure
code (REQ-253).
