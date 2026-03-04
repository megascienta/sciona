# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared helpers for overlay patching."""

from __future__ import annotations

import json
from typing import Optional

from ..types import OverlayPayload


def iter_node_changes(overlay: OverlayPayload) -> list[dict[str, object]]:
    changes: list[dict[str, object]] = []
    for diff_kind, entries in overlay.nodes.items():
        for entry in entries:
            record = dict(entry)
            record["diff_kind"] = diff_kind
            changes.append(record)
    return changes


def iter_edge_changes(overlay: OverlayPayload) -> list[dict[str, object]]:
    changes: list[dict[str, object]] = []
    for diff_kind, entries in overlay.edges.items():
        for entry in entries:
            record = dict(entry)
            record["diff_kind"] = diff_kind
            changes.append(record)
    return changes


def node_from_value(value: str | None) -> Optional[dict[str, object]]:
    if not value:
        return None
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    return decoded


def edge_from_value(value: str | None) -> Optional[dict[str, object]]:
    if not value:
        return None
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    return decoded


def module_for_node(node_type: str, qualified_name: str) -> Optional[str]:
    if node_type == "module":
        return qualified_name
    parts = qualified_name.split(".")
    if not parts:
        return None
    if node_type == "callable":
        if len(parts) >= 3:
            return ".".join(parts[:-2])
        if len(parts) >= 2:
            return ".".join(parts[:-1])
        return None
    if len(parts) >= 2:
        return ".".join(parts[:-1])
    return None


def module_in_scope(module_name: str, target: str) -> bool:
    if module_name == target:
        return True
    return target.startswith(f"{module_name}.")
