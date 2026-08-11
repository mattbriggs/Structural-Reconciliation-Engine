# Confidence

The system maintains **separate** confidence dimensions (REQ-276–279):

| Dimension | Meaning |
|---|---|
| Match | Likelihood two nodes are the same logical object |
| Operation | Likelihood the classified operation explains the relationship |
| Suppression | Likelihood a derived effect is fully explained by a root operation |
| Repair | Likelihood a proposed correction is appropriate and safe |

Rules:

- Repair confidence is **not** a copy of match confidence — it is derived
  conservatively and bounded below diagnostic confidence (REQ-276).
- Calibration metadata identifies the calibration model, or marks the value
  **uncalibrated** (REQ-277). An uncalibrated numeric value is a *score*, not a
  calibrated probability (REQ-278).
- Every threshold declares which confidence dimension it applies to (REQ-279).

In the initial release all confidence is uncalibrated; a labeled calibration
corpus is an open question.
