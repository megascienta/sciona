# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Plugin-facing SCIONA API (stable, read-only)."""

from __future__ import annotations

from ..runtime.addon_api import Registry
from ..runtime.addon_contract import (
    PLUGIN_API_MAJOR,
    PLUGIN_API_MINOR,
    PLUGIN_API_VERSION,
)
from ..pipelines.reducers import emit, list_entries
from .storage import (
    artifact_readonly,
    core_readonly,
    open_artifact_readonly,
    open_core_readonly,
)

__all__ = [
    "PLUGIN_API_VERSION",
    "PLUGIN_API_MAJOR",
    "PLUGIN_API_MINOR",
    "Registry",
    "emit",
    "list_entries",
    "open_core_readonly",
    "open_artifact_readonly",
    "core_readonly",
    "artifact_readonly",
]
