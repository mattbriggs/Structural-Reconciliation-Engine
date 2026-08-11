"""Version manifest for the Structural Reconciliation Engine.

Externally observable result schemas are versioned independently of the
package release so that downstream integrations can detect incompatible
changes (REQ-152, REQ-232, REQ-283).
"""

from __future__ import annotations

#: Distribution / release version of the package.
__version__ = "0.1.0"

#: Version of the reusable core reconciliation result contract.
CORE_CONTRACT_VERSION = "core-result-v1"

#: Version of the canonical tree input contract consumed by the core.
CANONICAL_TREE_CONTRACT_VERSION = "canonical-tree-v1"

#: Version of the localization application result contract.
LOCALIZATION_RESULT_CONTRACT_VERSION = "localization-result-v1"

#: Version of the tabular/serialized report contract (CSV/JSON rows).
REPORT_CONTRACT_VERSION = "report-v1"

#: Version of the reconciliation engine implementation itself.
ENGINE_VERSION = __version__
