# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Plugin-facing SCIONA API (stable, addon-safe)."""

from __future__ import annotations

from .reducers import emit, get_entry, list_entries
from .storage import (
    artifact_readonly,
    core_readonly,
    open_artifact_readonly,
    open_core_readonly,
)
from ..runtime.addons.contract import (
    PLUGIN_API_MAJOR,
    PLUGIN_API_MINOR,
    PLUGIN_API_VERSION,
)

__all__ = [
    "PLUGIN_API_VERSION",
    "PLUGIN_API_MAJOR",
    "PLUGIN_API_MINOR",
    "list_entries",
    "get_entry",
    "emit",
    "open_core_readonly",
    "open_artifact_readonly",
    "core_readonly",
    "artifact_readonly",
]
