# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Diff overlay scope resolution and affection matching."""

from __future__ import annotations

import json

from .types import OverlayPayload


def extract_scope_hint(
    payload: dict[str, object], profile: dict[str, object] | None
) -> dict[str, object]:
    scope: dict[str, object] = {"scope": "unknown"}
    scope_type = str(profile.get("scope_type")) if profile else "unknown"
    if scope_type == "module":
        module_name = payload.get("module_qualified_name") or payload.get("module_filter")
        scope = {
            "scope": "module",
            "module_qualified_name": module_name,
            "module_structural_id": payload.get("module_structural_id")
            or payload.get("module_filter"),
        }
    elif scope_type == "callable":
        scope = {
            "scope": "callable",
            "callable_id": payload.get("callable_id") or payload.get("function_id"),
            "qualified_name": payload.get("qualified_name")
            or payload.get("identity", {}).get("qualified_name"),
        }
    elif scope_type == "class":
        scope = {
            "scope": "class",
            "class_id": payload.get("class_id"),
            "qualified_name": payload.get("qualified_name"),
        }
    elif scope_type == "file":
        scope = {
            "scope": "file",
            "file_path": payload.get("file_path"),
            "module_filter": payload.get("module_filter"),
        }
    elif scope_type == "codebase":
        scope = {"scope": "codebase"}
    elif scope_type == "query":
        scope = {"scope": "query", "query": payload.get("query")}
    elif scope_type == "fan":
        node_id = payload.get("node_id")
        if node_id:
            scope = {
                "scope": "fan",
                "node_id": node_id,
                "module_id": payload.get("module_id"),
                "class_id": payload.get("class_id"),
                "callable_id": payload.get("callable_id") or payload.get("function_id"),
            }
        else:
            scope = {"scope": "codebase"}
    return scope


def scoped_affection(
    overlay: OverlayPayload,
    scope: dict[str, object],
    profile: dict[str, object] | None,
) -> tuple[bool | None, list[str]]:
    if not overlay:
        return None, []
    scope_type = str(scope.get("scope") or "unknown")
    affected_by = [str(item) for item in (profile or {}).get("affected_by", [])]
    if scope_type == "unknown":
        return None, affected_by

    module_name = scope.get("module_qualified_name")
    file_path = scope.get("file_path")
    module_filter = scope.get("module_filter")
    class_id = scope.get("class_id")
    callable_id = scope.get("callable_id")
    node_id = scope.get("node_id")
    query = scope.get("query")
    class_qualified = scope.get("qualified_name")
    if scope_type == "callable" and not callable_id:
        return None, affected_by
    if scope_type == "class" and not (class_id or class_qualified):
        return None, affected_by
    if scope_type == "class" and "calls" in affected_by and not class_qualified:
        return None, affected_by
    if scope_type == "module" and not (module_name or module_filter):
        return None, affected_by
    if scope_type == "file" and not file_path:
        return None, affected_by
    if scope_type == "fan" and not node_id:
        return None, affected_by
    if scope_type == "query" and not query:
        return None, affected_by

    def _module_match(name: str | None) -> bool:
        if not name:
            return False
        target = module_name or module_filter
        if not target:
            return False
        return name == target or name.startswith(f"{target}.")

    def _query_match(value: str | None) -> bool:
        if not value or not query:
            return False
        tokens = [tok for tok in str(query).lower().split() if tok]
        if not tokens:
            return False
        text = str(value).lower()
        return all(token in text for token in tokens)

    def _node_match(entry: dict[str, object]) -> bool:
        if scope_type == "codebase":
            return True
        meta = _parse_overlay_value(entry)
        qualified = meta.get("qualified_name")
        if scope_type == "file":
            return bool(file_path and meta.get("file_path") == file_path)
        if scope_type == "module":
            return _module_match(str(qualified)) or _module_match(str(meta.get("module")))
        if scope_type == "callable":
            return str(entry.get("structural_id")) == str(callable_id)
        if scope_type == "class":
            if str(entry.get("structural_id")) == str(class_id):
                return True
            if class_qualified and qualified:
                return str(qualified).startswith(f"{class_qualified}.")
            return False
        if scope_type == "fan":
            return str(entry.get("structural_id")) == str(node_id)
        if scope_type == "query":
            return _query_match(str(qualified)) or _query_match(str(meta.get("file_path")))
        return False

    def _edge_match(entry: dict[str, object]) -> bool:
        if scope_type == "codebase":
            return True
        meta = _parse_overlay_value(entry)
        src_name = meta.get("src_qualified_name")
        dst_name = meta.get("dst_qualified_name")
        if scope_type == "file":
            return bool(
                file_path
                and (meta.get("src_file_path") == file_path or meta.get("dst_file_path") == file_path)
            )
        if scope_type == "module":
            return _module_match(str(src_name)) or _module_match(str(dst_name))
        if scope_type == "fan":
            return str(meta.get("src_structural_id")) == str(node_id) or str(
                meta.get("dst_structural_id")
            ) == str(node_id)
        return False

    def _call_match(entry: dict[str, object]) -> bool:
        if scope_type == "codebase":
            return True
        if scope_type == "callable":
            return str(entry.get("src_structural_id")) == str(callable_id) or str(
                entry.get("dst_structural_id")
            ) == str(callable_id)
        if scope_type == "module":
            src_name = entry.get("src_qualified_name")
            dst_name = entry.get("dst_qualified_name")
            return _module_match(str(src_name)) or _module_match(str(dst_name))
        if scope_type == "class":
            src_name = entry.get("src_qualified_name")
            dst_name = entry.get("dst_qualified_name")
            if not class_qualified:
                return False
            return str(src_name).startswith(f"{class_qualified}.") or str(dst_name).startswith(
                f"{class_qualified}."
            )
        if scope_type == "file":
            return bool(
                file_path
                and (entry.get("src_file_path") == file_path or entry.get("dst_file_path") == file_path)
            )
        if scope_type == "fan":
            return str(entry.get("src_structural_id")) == str(node_id) or str(
                entry.get("dst_structural_id")
            ) == str(node_id)
        return False

    def _has_scoped(kind: str) -> bool:
        if kind == "nodes":
            for entries in overlay.nodes.values():
                for entry in entries:
                    if _node_match(entry):
                        return True
        if kind == "edges":
            for entries in overlay.edges.values():
                for entry in entries:
                    if _edge_match(entry):
                        return True
        if kind == "calls":
            for entries in overlay.calls.values():
                for entry in entries:
                    if _call_match(entry):
                        return True
        return False

    affected = any(_has_scoped(kind) for kind in affected_by)
    return affected, affected_by


def _parse_overlay_value(entry: dict[str, object]) -> dict[str, object]:
    raw = entry.get("new_value") or entry.get("old_value")
    if not isinstance(raw, str) or not raw:
        return {}
    try:
        value = json.loads(raw)
    except Exception:
        return {}
    if isinstance(value, dict):
        return value
    return {}


__all__ = ["extract_scope_hint", "scoped_affection"]
