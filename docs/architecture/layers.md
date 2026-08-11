# Layers & dependency rules

Dependencies point **inward**. The core depends on nothing else in the system;
outer layers depend on inner interfaces.

## Rules

- Delivery may depend on application interfaces; it never orchestrates core
  modules directly (REQ-247).
- Application depends on core interfaces and typed profiles (REQ-248).
- Core depends on **no** application, delivery, report, persistence, CCMS,
  localization, or pricing component (REQ-249).
- Infrastructure implements ports declared by the application/domain (REQ-250).
- Pricing consumes result contracts and cannot influence reconciliation
  (REQ-251, AC-035).
- Renderers consume immutable results and never alter conclusions (REQ-252).

## The core independence boundary (AC-031)

`reconciliation.core` can be imported and fully tested using only in-memory
canonical trees and typed profiles. This is enforced mechanically:
`tests/contract/test_core_independence.py` imports the core in a subprocess and
asserts that no forbidden module (lxml, fastapi, sqlalchemy, jinja2, or any
`reconciliation.{adapters,application,infrastructure,reporting,delivery,…}`
package) is present in `sys.modules`.

Treat that boundary as an architectural release test, not merely a packaging
convention.
