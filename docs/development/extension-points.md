# Extension points

The system is designed to be extended without touching the core.

| To add… | Do this | Guarantee |
|---|---|---|
| A **document adapter** | implement `DocumentAdapter` (produce a `CanonicalTree`) and register it in a `DocumentProfileRegistry` | no core change (AC-032) |
| An **operation classifier** | implement the classifier protocol and register it | no matcher/aligner change (REQ-062, AC-032) |
| A **report renderer** | consume the versioned `LocalizationValidationResult` / `ReportTable` | no reconciliation change (AC-034) |
| A **repository / artifact store** | implement the port in `application.ports` | application runs against fakes or your backend |
| A **non-localization application** | consume `ReconciliationResult` directly | no dependency on locale/repair terms (AC-033) |
| A **CCMS integration** | implement `CCMSReadPort` (read-only) | failures isolated as `CCMS_READ_FAILED` (REQ-190) |
| A **pricing model** | consume `PricingInputMetrics` | cannot alter reconciliation (AC-035) |

Prefer Python constructor injection plus protocols. The initial release
deliberately avoids an event bus, DI framework, workflow engine, or plugin
framework.

## Built-in document adapters

The default registry wires these document profiles:

| Profile id | Adapter |
|---|---|
| `dita-map-v1` | DITA map XML adapter |
| `generic-xml-v1` | Generic XML adapter |
| `generic-json-v1` | Generic JSON data-tree adapter |
| `generic-yaml-v1` | Generic YAML data-tree adapter |

JSON and YAML share the `data:*` canonical node model. To add a domain-specific
JSON or YAML profile, compose the safe parser and shared data-tree builder, then
promote only domain-approved fields into identity properties in the adapter.
