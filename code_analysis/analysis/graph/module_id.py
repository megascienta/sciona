"""Module-id helpers for graph analysis."""

from __future__ import annotations

from typing import Set


def module_id_for(qualified_name: str, module_names: Set[str]) -> str:
    if not qualified_name:
        return ""
    if qualified_name in module_names:
        return qualified_name
    parts = qualified_name.split(".")
    for end in range(len(parts) - 1, 0, -1):
        candidate = ".".join(parts[:end])
        if candidate in module_names:
            return candidate
    return parts[0]


__all__ = ["module_id_for"]
