"""Report renderers over the immutable localization result (REQ-148-159).

Renderers consume a
:class:`~reconciliation.application.contracts.localization.LocalizationValidationResult`
and produce JSON, CSV, a summary, or a self-contained HTML report. They never
alter reconciliation conclusions (REQ-252) and a renderer failure never
invalidates the underlying result (REQ-173, SRS §8.8 ``REPORT_GENERATION_FAILED``).
"""

from __future__ import annotations
