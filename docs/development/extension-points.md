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
