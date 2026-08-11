# Security

XML input is treated as untrusted (REQ-216).

## XML hardening (REQ-217, REQ-218)

The parser (`reconciliation.adapters.xml.parser.SecureXmlParser`):

- disables external entity resolution and installs a blocking resolver (XXE);
- never expands internal entities and rejects residual entity references
  (billion-laughs);
- never loads an external DTD (a DITA `DOCTYPE` is allowed but its external
  subset is not fetched);
- bounds input size, element nesting depth, and total node count.

Verified by `tests/security/test_xml_hardening.py`.

## HTML report safety (REQ-219, REQ-147)

Report content is escaped by Jinja2 autoescaping; only the report's own CSS/JS
is marked safe. Script-like content is rendered inert
(`test_ac_026_html_safety_escapes_scriptish_content`).

## Secrets, redaction, and paths (REQ-220–222, REQ-182)

- Structured logs always mask credential-like keys and, by default, content
  values; see [Observability](../operations/observability.md).
- API responses omit filesystem artifact locations unless explicitly enabled.
- The filesystem artifact store rejects path-traversal components.

## Network & privacy (REQ-223–224)

The core requires no network access; deployments can run entirely within an
organization-controlled environment.
