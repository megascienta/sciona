"""Plugin-facing SCIONA API (stable, read-only)."""
from __future__ import annotations

from ..runtime.addon_api import Registry
from ..runtime.addon_contract import (
    PLUGIN_API_MAJOR,
    PLUGIN_API_MINOR,
    PLUGIN_API_VERSION,
)
from ..pipelines.prompt import compile_prompt_payload
from ..pipelines.reducers import emit

__all__ = [
    "PLUGIN_API_VERSION",
    "PLUGIN_API_MAJOR",
    "PLUGIN_API_MINOR",
    "Registry",
    "compile_prompt_payload",
    "emit",
]
