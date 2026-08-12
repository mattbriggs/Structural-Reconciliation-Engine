# CLI

The CLI is an optional delivery layer. The base install is the reusable core
only, so install the `cli` extra before using the console script — it carries
typer plus the XML/DITA parser, YAML profile loader, and HTML renderer that the
default document-profile path composes:

```bash
python -m pip install "structural-reconciliation[cli]"
```

Without it, `reconcile-localization` exits with one line naming the missing
dependency rather than an import traceback.

Built-in document profile ids:

| Profile id | Input shape |
|---|---|
| `dita-map-v1` | DITA map XML (default) |
| `generic-xml-v1` | Vocabulary-agnostic XML |
| `generic-json-v1` | JSON data trees |
| `generic-yaml-v1` | YAML data trees |

```bash
reconcile-localization \
  --source source.ditamap \
  --locale fr-FR.ditamap \
  --locale-code fr-FR \
  --document-profile dita-map-v1 \
  --html report.html \
  --csv report.csv \
  --json result.json
```

Generic JSON example:

```bash
reconcile-localization \
  --source source.json \
  --locale target.json \
  --locale-code und \
  --document-profile generic-json-v1 \
  --json result.json
```

Generic YAML example:

```bash
reconcile-localization \
  --source source.yaml \
  --locale target.yaml \
  --locale-code und \
  --document-profile generic-yaml-v1 \
  --json result.json
```

## Options

| Option | Meaning |
|---|---|
| `--source`, `--locale` | Input document paths |
| `--locale-code` | Locale code, e.g. `fr-FR` |
| `--document-profile` | Profile id (default `dita-map-v1`; generic XML/JSON/YAML profiles are registered) |
| `--html`, `--csv`, `--json` | Write the respective artifact |
| `--machine-errors` | Emit machine-readable JSON output/errors (REQ-185) |
| `--treat-findings-as-failure / --no-...` | Whether findings affect the exit code |

## Exit codes (REQ-183, REQ-184)

The exit-code policy separates technical failures from content findings:

| Code | Meaning |
|---|---|
| `0` | Completed with no blocking findings |
| `1` | Technical failure (invalid input, engine/profile error) |
| `2` | Completed with blocking content findings |
