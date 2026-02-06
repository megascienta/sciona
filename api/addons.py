"""Plugin-facing SCIONA API (stable, read-only)."""

from __future__ import annotations

from ..runtime import addons as addon_runtime
from ..runtime.addon_api import Registry
from ..runtime.addon_contract import (
    PLUGIN_API_MAJOR,
    PLUGIN_API_MINOR,
    PLUGIN_API_VERSION,
)
from ..pipelines.prompt import compile_prompt_payload
from ..pipelines.reducers import emit, list_entries

load_for_cli = addon_runtime.load_for_cli

__all__ = [
    "PLUGIN_API_VERSION",
    "PLUGIN_API_MAJOR",
    "PLUGIN_API_MINOR",
    "Registry",
    "load_for_cli",
    "compile_prompt_payload",
    "emit",
    "list_entries",
]
