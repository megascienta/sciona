"""Plugin-facing SCIONA API (stable, read-only)."""
from __future__ import annotations

from ..runtime.addon_api import Registry
from ..pipelines.prompt import compile_prompt_payload
from ..pipelines.reducers import emit

__all__ = [
    "Registry",
    "compile_prompt_payload",
    "emit",
]
