# CLI

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

## Options

| Option | Meaning |
|---|---|
| `--source`, `--locale` | Input document paths |
| `--locale-code` | Locale code, e.g. `fr-FR` |
| `--document-profile` | Profile id (default `dita-map-v1`) |
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
