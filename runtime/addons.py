# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Addon registry helpers (library-only)."""

from __future__ import annotations

from importlib import metadata


def discover_entry_points() -> dict[str, metadata.EntryPoint]:
    """Expose entry points for external addon launchers (no auto-load)."""
    entries = metadata.entry_points()
    group = entries.select(group="sciona.addons")
    discovered: dict[str, metadata.EntryPoint] = {}
    for entry in group:
        discovered[entry.name] = entry
    return discovered
