"""Thin shim module for `python -m nexuscli.orchestrator`.

This re-exports the core orchestrator symbols so existing tooling can import
`nexuscli.orchestrator` while the implementation remains in `core.orchestrator`.
"""

from core.orchestrator import Orchestrator  # re-export for convenience

__all__ = ["Orchestrator"]

