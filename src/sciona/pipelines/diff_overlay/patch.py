# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Overlay patching for reducer payloads."""

from __future__ import annotations

import json
from typing import Optional

from .types import OverlayPayload
from ...runtime import identity as ids


def apply_overlay_to_payload(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
    reducer_id: str | None = None,
) -> tuple[dict[str, object], bool]:
    projection = _resolve_projection(payload, reducer_id)
    if projection == "structural_index":
        return patch_structural_index(payload, overlay), True
    if projection == "module_overview":
        return patch_module_overview(payload, overlay), True
    if projection == "callable_overview":
        return patch_callable_overview(payload, overlay), True
    if projection == "class_overview":
        return patch_class_overview(payload, overlay), True
    if projection == "file_outline":
        return patch_file_outline(payload, overlay), True
    if projection == "module_file_map":
        return patch_module_file_map(payload, overlay), True
    if projection == "dependency_edges":
        return patch_dependency_edges(payload, overlay), True
    if projection == "import_targets":
        return patch_import_targets(payload, overlay), True
    if projection == "importers_index":
        return patch_importers_index(payload, overlay), True
    if projection == "symbol_lookup":
        return patch_symbol_lookup(payload, overlay), True
    if projection == "symbol_references":
        return patch_symbol_references(payload, overlay), True
    if projection == "call_neighbors":
        return patch_call_neighbors(payload, overlay, snapshot_id=snapshot_id, conn=conn), True
    if projection == "callsite_index":
        return patch_callsite_index(payload, overlay, snapshot_id=snapshot_id, conn=conn), True
    if projection == "class_call_graph_summary":
        return patch_class_call_graph_summary(
            payload, overlay, snapshot_id=snapshot_id, conn=conn
        ), True
    if projection == "module_call_graph_summary":
        return patch_module_call_graph_summary(
            payload, overlay, snapshot_id=snapshot_id, conn=conn
        ), True
    if projection == "fan_summary":
        return patch_fan_summary(payload, overlay, snapshot_id=snapshot_id, conn=conn), True
    if projection == "hotspot_summary":
        return patch_hotspot_summary(payload, overlay, snapshot_id=snapshot_id, conn=conn), True
    return payload, False


def _resolve_projection(payload: dict[str, object], reducer_id: str | None) -> str:
    projection = str(payload.get("projection", "")).strip().lower()
    if projection:
        return projection
    return str(reducer_id or "").strip().lower()


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
    if node_type == "method":
        if len(parts) >= 3:
            return ".".join(parts[:-2])
        return None
    if len(parts) >= 2:
        return ".".join(parts[:-1])
    return None


def module_in_scope(module_name: str, target: str) -> bool:
    if module_name == target:
        return True
    return target.startswith(f"{module_name}.")


def patch_structural_index(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    modules = list((payload.get("modules") or {}).get("entries", []) or [])
    files = list((payload.get("files") or {}).get("entries", []) or [])
    classes = list((payload.get("classes") or {}).get("entries", []) or [])
    functions = list((payload.get("functions") or {}).get("by_module", []) or [])
    methods = list((payload.get("methods") or {}).get("by_module", []) or [])

    module_map = {
        entry.get("module_qualified_name"): entry
        for entry in modules
        if entry.get("module_qualified_name")
    }
    file_map = {entry.get("path"): entry for entry in files if entry.get("path")}
    class_ids = {
        entry.get("structural_id") for entry in classes if entry.get("structural_id")
    }
    function_counts = {
        entry.get("module_qualified_name"): entry.get("count", 0) for entry in functions
    }
    method_counts = {
        entry.get("module_qualified_name"): entry.get("count", 0) for entry in methods
    }
    class_counts = {
        entry.get("module_qualified_name"): entry.get("count", 0)
        for entry in payload.get("classes", {}).get("by_module", []) or []
    }

    for change in iter_node_changes(overlay):
        node = node_from_value(change.get("new_value") or change.get("old_value"))
        if not node:
            continue
        node_type = str(node.get("node_type", ""))
        qualified_name = str(node.get("qualified_name", ""))
        module_name = module_for_node(node_type, qualified_name)
        file_path = node.get("file_path")
        if change["diff_kind"] == "add":
            if node_type == "module" and module_name:
                module_map.setdefault(
                    module_name,
                    {
                        "module_qualified_name": module_name,
                        "language": node.get("language"),
                        "file_count": 0,
                        "class_count": 0,
                        "function_count": 0,
                        "method_count": 0,
                    },
                )
            if node_type == "class" and node.get("structural_id") not in class_ids:
                classes.append(
                    {
                        "structural_id": node.get("structural_id"),
                        "qualified_name": qualified_name,
                        "module_qualified_name": module_name,
                        "language": node.get("language"),
                        "file_path": file_path,
                        "line_span": [node.get("start_line"), node.get("end_line")],
                    }
                )
                class_ids.add(node.get("structural_id"))
                if module_name:
                    class_counts[module_name] = class_counts.get(module_name, 0) + 1
            if node_type == "function" and module_name:
                function_counts[module_name] = function_counts.get(module_name, 0) + 1
            if node_type == "method" and module_name:
                method_counts[module_name] = method_counts.get(module_name, 0) + 1
            if file_path and file_path not in file_map:
                file_map[file_path] = {
                    "path": file_path,
                    "module_qualified_name": module_name,
                }
        elif change["diff_kind"] == "remove":
            if node_type == "class":
                classes = [
                    entry
                    for entry in classes
                    if entry.get("structural_id") != node.get("structural_id")
                ]
                if module_name:
                    class_counts[module_name] = max(
                        0, class_counts.get(module_name, 0) - 1
                    )
            if node_type == "function" and module_name:
                function_counts[module_name] = max(
                    0, function_counts.get(module_name, 0) - 1
                )
            if node_type == "method" and module_name:
                method_counts[module_name] = max(
                    0, method_counts.get(module_name, 0) - 1
                )

    modules = list(module_map.values())
    for entry in modules:
        module_name = entry.get("module_qualified_name")
        entry["class_count"] = class_counts.get(
            module_name, entry.get("class_count", 0)
        )
        entry["function_count"] = function_counts.get(
            module_name, entry.get("function_count", 0)
        )
        entry["method_count"] = method_counts.get(
            module_name, entry.get("method_count", 0)
        )
    import_edges = list((payload.get("imports") or {}).get("edges", []) or [])
    import_key = lambda entry: (
        entry.get("from_module_qualified_name"),
        entry.get("to_module_qualified_name"),
    )
    import_map = {import_key(entry): entry for entry in import_edges}
    for change in iter_edge_changes(overlay):
        edge = edge_from_value(change.get("new_value") or change.get("old_value"))
        if not edge or edge.get("edge_type") != "IMPORTS_DECLARED":
            continue
        src_name = edge.get("src_qualified_name")
        dst_name = edge.get("dst_qualified_name")
        if not src_name or not dst_name:
            continue
        key = (src_name, dst_name)
        if change["diff_kind"] == "add":
            import_map[key] = {
                "from_module_qualified_name": src_name,
                "to_module_qualified_name": dst_name,
            }
        elif change["diff_kind"] == "remove":
            import_map.pop(key, None)
    payload["imports"]["edges"] = sorted(
        import_map.values(),
        key=lambda item: (
            str(item.get("from_module_qualified_name")),
            str(item.get("to_module_qualified_name")),
        ),
    )
    payload["imports"]["edge_count"] = len(payload["imports"]["edges"])
    payload["modules"]["entries"] = sorted(
        modules, key=lambda item: str(item.get("module_qualified_name"))
    )
    payload["modules"]["count"] = len(payload["modules"]["entries"])
    payload["files"]["entries"] = sorted(
        file_map.values(), key=lambda item: str(item.get("path"))
    )
    payload["files"]["count"] = len(payload["files"]["entries"])
    payload["classes"]["entries"] = sorted(
        classes, key=lambda item: str(item.get("qualified_name"))
    )
    payload["classes"]["count"] = len(payload["classes"]["entries"])
    payload["classes"]["by_module"] = [
        {"module_qualified_name": module, "count": count}
        for module, count in sorted(class_counts.items())
        if count
    ]
    payload["functions"]["by_module"] = [
        {"module_qualified_name": module, "count": count}
        for module, count in sorted(function_counts.items())
        if count
    ]
    payload["methods"]["by_module"] = [
        {"module_qualified_name": module, "count": count}
        for module, count in sorted(method_counts.items())
        if count
    ]
    return payload


def patch_module_overview(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    module_name = str(payload.get("module_qualified_name", "")).strip()
    if not module_name:
        return payload
    files = set(payload.get("files", []) or [])
    classes = list(payload.get("classes", []) or [])
    functions = list(payload.get("functions", []) or [])
    methods = list(payload.get("methods", []) or [])
    imports = list(payload.get("imports", []) or [])

    class_ids = {
        entry.get("structural_id") for entry in classes if entry.get("structural_id")
    }
    function_ids = {
        entry.get("structural_id") for entry in functions if entry.get("structural_id")
    }
    method_ids = {
        entry.get("structural_id") for entry in methods if entry.get("structural_id")
    }
    import_ids = {
        entry.get("module_structural_id")
        for entry in imports
        if entry.get("module_structural_id")
    }

    for change in iter_node_changes(overlay):
        node = node_from_value(change.get("new_value") or change.get("old_value"))
        if not node:
            continue
        node_type = str(node.get("node_type", ""))
        qualified_name = str(node.get("qualified_name", ""))
        node_module = module_for_node(node_type, qualified_name)
        if not node_module or not module_in_scope(module_name, node_module):
            continue
        if change["diff_kind"] == "add":
            if node_type == "class" and node.get("structural_id") not in class_ids:
                classes.append(
                    {
                        "structural_id": node.get("structural_id"),
                        "qualified_name": qualified_name,
                    }
                )
                class_ids.add(node.get("structural_id"))
            if (
                node_type == "function"
                and node.get("structural_id") not in function_ids
            ):
                functions.append(
                    {
                        "structural_id": node.get("structural_id"),
                        "qualified_name": qualified_name,
                    }
                )
                function_ids.add(node.get("structural_id"))
            if node_type == "method" and node.get("structural_id") not in method_ids:
                methods.append(
                    {
                        "structural_id": node.get("structural_id"),
                        "qualified_name": qualified_name,
                    }
                )
                method_ids.add(node.get("structural_id"))
            file_path = node.get("file_path")
            if file_path:
                files.add(file_path)
        elif change["diff_kind"] == "remove":
            if node_type == "class":
                classes = [
                    entry
                    for entry in classes
                    if entry.get("structural_id") != node.get("structural_id")
                ]
            if node_type == "function":
                functions = [
                    entry
                    for entry in functions
                    if entry.get("structural_id") != node.get("structural_id")
                ]
            if node_type == "method":
                methods = [
                    entry
                    for entry in methods
                    if entry.get("structural_id") != node.get("structural_id")
                ]
        elif change["diff_kind"] == "modify":
            if node_type == "module" and node.get("structural_id") == payload.get(
                "module_structural_id"
            ):
                if change.get("field") == "file_path":
                    payload["file_path"] = change.get("new_value")
                if change.get("field") == "start_line":
                    line_span = payload.get("line_span") or []
                    if isinstance(line_span, list) and line_span:
                        line_span[0] = int(change.get("new_value") or line_span[0])
                        payload["line_span"] = line_span
                if change.get("field") == "end_line":
                    line_span = payload.get("line_span") or []
                    if isinstance(line_span, list) and line_span:
                        line_span[1] = int(change.get("new_value") or line_span[1])
                        payload["line_span"] = line_span
                if change.get("field") == "content_hash":
                    payload["content_hash"] = change.get("new_value")

    for change in iter_edge_changes(overlay):
        edge = edge_from_value(change.get("new_value") or change.get("old_value"))
        if not edge or edge.get("edge_type") != "IMPORTS_DECLARED":
            continue
        src_name = edge.get("src_qualified_name")
        if not src_name or not module_in_scope(module_name, str(src_name)):
            continue
        dst_id = edge.get("dst_structural_id")
        dst_name = edge.get("dst_qualified_name")
        if change["diff_kind"] == "add":
            if dst_id and dst_id not in import_ids:
                imports.append(
                    {"module_structural_id": dst_id, "module_qualified_name": dst_name}
                )
                import_ids.add(dst_id)
        elif change["diff_kind"] == "remove":
            imports = [
                entry
                for entry in imports
                if entry.get("module_structural_id") != dst_id
            ]

    payload["files"] = sorted(files)
    payload["file_count"] = len(payload["files"])
    payload["classes"] = sorted(
        classes, key=lambda item: str(item.get("qualified_name"))
    )
    payload["functions"] = sorted(
        functions, key=lambda item: str(item.get("qualified_name"))
    )
    payload["methods"] = sorted(
        methods, key=lambda item: str(item.get("qualified_name"))
    )
    payload["node_counts"] = {
        "classes": len(payload["classes"]),
        "functions": len(payload["functions"]),
        "methods": len(payload["methods"]),
    }
    payload["imports"] = sorted(
        imports, key=lambda item: str(item.get("module_qualified_name"))
    )
    return payload


def patch_callable_overview(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    structural_id = payload.get("function_id") or payload.get("callable_id")
    if not structural_id:
        return payload
    for change in iter_node_changes(overlay):
        if change.get("structural_id") != structural_id:
            continue
        if change.get("diff_kind") != "modify":
            continue
        field = change.get("field")
        if field == "file_path":
            payload["file_path"] = change.get("new_value")
        elif field == "start_line":
            line_span = payload.get("line_span") or []
            if isinstance(line_span, list) and line_span:
                line_span[0] = int(change.get("new_value") or line_span[0])
                payload["line_span"] = line_span
        elif field == "end_line":
            line_span = payload.get("line_span") or []
            if isinstance(line_span, list) and line_span:
                line_span[1] = int(change.get("new_value") or line_span[1])
                payload["line_span"] = line_span
        elif field == "content_hash":
            payload["content_hash"] = change.get("new_value")
    return payload


def patch_class_overview(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    class_id = payload.get("class_id")
    if not class_id:
        return payload
    methods = list(payload.get("methods", []) or [])
    method_ids = {
        entry.get("function_id") for entry in methods if entry.get("function_id")
    }
    for change in iter_node_changes(overlay):
        node = node_from_value(change.get("new_value") or change.get("old_value"))
        if not node:
            continue
        node_type = node.get("node_type")
        if (
            node_type == "class"
            and node.get("structural_id") == class_id
            and change.get("diff_kind") == "modify"
        ):
            if change.get("field") == "file_path":
                payload["file_path"] = change.get("new_value")
            if change.get("field") == "start_line":
                span = list(payload.get("line_span") or [])
                if len(span) == 2:
                    span[0] = int(change.get("new_value") or span[0])
                    payload["line_span"] = span
            if change.get("field") == "end_line":
                span = list(payload.get("line_span") or [])
                if len(span) == 2:
                    span[1] = int(change.get("new_value") or span[1])
                    payload["line_span"] = span
            if change.get("field") == "content_hash":
                payload["content_hash"] = change.get("new_value")
        if node_type == "method":
            parent_module = module_for_node(
                "method", str(node.get("qualified_name", ""))
            )
            if (
                payload.get("module_qualified_name")
                and parent_module
                and not module_in_scope(
                    str(payload.get("module_qualified_name")), parent_module
                )
            ):
                continue
            if (
                change.get("diff_kind") == "add"
                and node.get("structural_id") not in method_ids
            ):
                methods.append(
                    {
                        "function_id": node.get("structural_id"),
                        "qualified_name": node.get("qualified_name"),
                    }
                )
                method_ids.add(node.get("structural_id"))
            if change.get("diff_kind") == "remove":
                methods = [
                    entry
                    for entry in methods
                    if entry.get("function_id") != node.get("structural_id")
                ]
    payload["methods"] = sorted(
        methods, key=lambda item: str(item.get("qualified_name"))
    )
    return payload


def patch_file_outline(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    files = list(payload.get("files", []) or [])
    file_map = {
        entry.get("file_path"): entry for entry in files if entry.get("file_path")
    }
    file_filter = payload.get("file_path")
    module_filter = payload.get("module_filter")
    for change in iter_node_changes(overlay):
        node = node_from_value(change.get("new_value") or change.get("old_value"))
        if not node:
            continue
        file_path = node.get("file_path")
        if not file_path:
            continue
        if file_filter and file_path != file_filter:
            continue
        qualified_name = str(node.get("qualified_name", ""))
        node_type = str(node.get("node_type", ""))
        module_name = module_for_node(node_type, qualified_name)
        if (
            module_filter
            and module_name
            and not module_in_scope(str(module_filter), module_name)
        ):
            continue
        entry = file_map.setdefault(
            file_path,
            {"file_path": file_path, "language": node.get("language"), "nodes": []},
        )
        nodes = list(entry.get("nodes", []) or [])
        if change["diff_kind"] == "add":
            nodes.append(
                {
                    "structural_id": node.get("structural_id"),
                    "qualified_name": qualified_name,
                    "node_type": node_type,
                    "module_qualified_name": module_name,
                    "line_span": [node.get("start_line"), node.get("end_line")],
                }
            )
        elif change["diff_kind"] == "remove":
            nodes = [
                item
                for item in nodes
                if item.get("structural_id") != node.get("structural_id")
            ]
        elif change["diff_kind"] == "modify":
            for item in nodes:
                if item.get("structural_id") != node.get("structural_id"):
                    continue
                if change.get("field") in {"start_line", "end_line"}:
                    span = list(item.get("line_span") or [])
                    if len(span) == 2:
                        if change.get("field") == "start_line":
                            span[0] = int(change.get("new_value") or span[0])
                        if change.get("field") == "end_line":
                            span[1] = int(change.get("new_value") or span[1])
                        item["line_span"] = span
                if change.get("field") == "qualified_name":
                    item["qualified_name"] = change.get("new_value")
        entry["nodes"] = sorted(
            nodes,
            key=lambda item: (
                item.get("line_span", [0, 0])[0],
                item.get("line_span", [0, 0])[1],
                str(item.get("qualified_name")),
            ),
        )
        file_map[file_path] = entry
    payload["files"] = [file_map[key] for key in sorted(file_map)]
    payload["count"] = len(payload["files"])
    return payload


def patch_module_file_map(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    modules = list(payload.get("modules", []) or [])
    module_map = {
        entry.get("module_structural_id"): entry
        for entry in modules
        if entry.get("module_structural_id")
    }
    module_filter = payload.get("module_filter")
    for change in iter_node_changes(overlay):
        node = node_from_value(change.get("new_value") or change.get("old_value"))
        if not node or node.get("node_type") != "module":
            continue
        module_name = node.get("qualified_name")
        if (
            module_filter
            and module_name
            and not module_in_scope(str(module_filter), str(module_name))
        ):
            continue
        structural_id = node.get("structural_id")
        if change["diff_kind"] == "add":
            module_map[structural_id] = {
                "module_qualified_name": module_name,
                "module_structural_id": structural_id,
                "language": node.get("language"),
                "file_path": node.get("file_path"),
                "line_span": [node.get("start_line"), node.get("end_line")],
            }
        elif change["diff_kind"] == "remove":
            module_map.pop(structural_id, None)
        elif change["diff_kind"] == "modify":
            entry = module_map.get(structural_id)
            if not entry:
                continue
            if change.get("field") == "file_path":
                entry["file_path"] = change.get("new_value")
            if change.get("field") == "start_line":
                span = list(entry.get("line_span") or [])
                if len(span) == 2:
                    span[0] = int(change.get("new_value") or span[0])
                    entry["line_span"] = span
            if change.get("field") == "end_line":
                span = list(entry.get("line_span") or [])
                if len(span) == 2:
                    span[1] = int(change.get("new_value") or span[1])
                    entry["line_span"] = span
    payload["modules"] = sorted(
        module_map.values(),
        key=lambda item: str(item.get("module_qualified_name")),
    )
    payload["count"] = len(payload["modules"])
    return payload


def patch_dependency_edges(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    edges = list(payload.get("edges", []) or [])
    edge_key = lambda entry: (
        entry.get("from_module_structural_id"),
        entry.get("to_module_structural_id"),
        entry.get("edge_type"),
    )
    edge_map = {edge_key(entry): entry for entry in edges}
    from_filter = payload.get("from_module_filter")
    to_filter = payload.get("to_module_filter")
    for change in iter_edge_changes(overlay):
        edge = edge_from_value(change.get("new_value") or change.get("old_value"))
        if not edge or edge.get("edge_type") != "IMPORTS_DECLARED":
            continue
        src_id = edge.get("src_structural_id")
        dst_id = edge.get("dst_structural_id")
        if (
            from_filter
            and edge.get("src_qualified_name")
            and not module_in_scope(
                str(from_filter), str(edge.get("src_qualified_name"))
            )
        ):
            continue
        if (
            to_filter
            and edge.get("dst_qualified_name")
            and not module_in_scope(
                str(to_filter), str(edge.get("dst_qualified_name"))
            )
        ):
            continue
        key = (src_id, dst_id, edge.get("edge_type"))
        if change["diff_kind"] == "add":
            edge_map[key] = {
                "from_module_structural_id": src_id,
                "to_module_structural_id": dst_id,
                "from_module_qualified_name": edge.get("src_qualified_name"),
                "to_module_qualified_name": edge.get("dst_qualified_name"),
                "from_file_path": edge.get("src_file_path"),
                "to_file_path": edge.get("dst_file_path"),
                "edge_type": edge.get("edge_type"),
                "edge_source": "overlay",
            }
        elif change["diff_kind"] == "remove":
            edge_map.pop(key, None)
    patched = sorted(edge_map.values(), key=edge_key)
    payload["edges"] = patched
    payload["edge_count"] = len(patched)
    return payload


def patch_import_targets(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    edges = list(payload.get("edges", []) or [])
    edge_key = lambda entry: (
        entry.get("from_module_structural_id"),
        entry.get("to_module_structural_id"),
        entry.get("edge_type"),
    )
    edge_map = {edge_key(entry): entry for entry in edges}
    target_ids = {
        target.get("module_structural_id")
        for target in payload.get("targets", []) or []
    }
    for change in iter_edge_changes(overlay):
        edge = edge_from_value(change.get("new_value") or change.get("old_value"))
        if not edge or edge.get("edge_type") != "IMPORTS_DECLARED":
            continue
        dst_id = edge.get("dst_structural_id")
        if target_ids and dst_id not in target_ids:
            continue
        key = (edge.get("src_structural_id"), dst_id, edge.get("edge_type"))
        if change["diff_kind"] == "add":
            edge_map[key] = {
                "from_module_structural_id": edge.get("src_structural_id"),
                "to_module_structural_id": dst_id,
                "from_module_qualified_name": edge.get("src_qualified_name"),
                "to_module_qualified_name": edge.get("dst_qualified_name"),
                "from_file_path": edge.get("src_file_path"),
                "to_file_path": edge.get("dst_file_path"),
                "edge_type": edge.get("edge_type"),
                "edge_source": "overlay",
            }
        elif change["diff_kind"] == "remove":
            edge_map.pop(key, None)
    patched = sorted(edge_map.values(), key=edge_key)
    payload["edges"] = patched
    payload["edge_count"] = len(patched)
    return payload


def patch_importers_index(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    target_ids = {
        target.get("module_structural_id")
        for target in payload.get("targets", []) or []
    }
    importer_map = {
        entry.get("module_structural_id"): entry
        for entry in payload.get("importers", []) or []
        if entry.get("module_structural_id")
    }
    for change in iter_edge_changes(overlay):
        edge = edge_from_value(change.get("new_value") or change.get("old_value"))
        if not edge or edge.get("edge_type") != "IMPORTS_DECLARED":
            continue
        dst_id = edge.get("dst_structural_id")
        if target_ids and dst_id not in target_ids:
            continue
        src_id = edge.get("src_structural_id")
        if change["diff_kind"] == "add":
            importer_map[src_id] = {
                "module_structural_id": src_id,
                "module_qualified_name": edge.get("src_qualified_name"),
                "file_path": edge.get("src_file_path"),
            }
        elif change["diff_kind"] == "remove":
            importer_map.pop(src_id, None)
    payload["importers"] = sorted(
        importer_map.values(),
        key=lambda item: str(item.get("module_qualified_name")),
    )
    payload["importer_count"] = len(payload["importers"])
    return payload


def patch_symbol_lookup(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    matches = list(payload.get("matches", []) or [])
    match_ids = {
        entry.get("structural_id") for entry in matches if entry.get("structural_id")
    }
    for change in iter_node_changes(overlay):
        node = node_from_value(change.get("new_value") or change.get("old_value"))
        if not node:
            continue
        if change["diff_kind"] == "add" and node.get("structural_id") not in match_ids:
            matches.append(
                {
                    "structural_id": node.get("structural_id"),
                    "node_type": node.get("node_type"),
                    "language": node.get("language"),
                    "qualified_name": node.get("qualified_name"),
                    "file_path": node.get("file_path"),
                    "score": 0.55,
                }
            )
            match_ids.add(node.get("structural_id"))
        elif change["diff_kind"] == "remove":
            matches = [
                entry
                for entry in matches
                if entry.get("structural_id") != node.get("structural_id")
            ]
    payload["matches"] = sorted(
        matches,
        key=lambda item: (
            -float(item.get("score", 0.0)),
            str(item.get("qualified_name")),
        ),
    )[: int(payload.get("limit") or 0) or len(matches)]
    return payload


def patch_symbol_references(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    matches = list(payload.get("matches", []) or [])
    match_ids = {
        entry.get("structural_id") for entry in matches if entry.get("structural_id")
    }
    for change in iter_node_changes(overlay):
        node = node_from_value(change.get("new_value") or change.get("old_value"))
        if not node:
            continue
        if change["diff_kind"] == "add" and node.get("structural_id") not in match_ids:
            matches.append(
                {
                    "structural_id": node.get("structural_id"),
                    "node_type": node.get("node_type"),
                    "language": node.get("language"),
                    "qualified_name": node.get("qualified_name"),
                    "file_path": node.get("file_path"),
                    "line_span": [node.get("start_line"), node.get("end_line")],
                    "score": 0.55,
                }
            )
            match_ids.add(node.get("structural_id"))
        elif change["diff_kind"] == "remove":
            matches = [
                entry
                for entry in matches
                if entry.get("structural_id") != node.get("structural_id")
            ]
    payload["matches"] = sorted(
        matches,
        key=lambda item: (
            -float(item.get("score", 0.0)),
            str(item.get("qualified_name")),
        ),
    )[: int(payload.get("limit") or 0) or len(matches)]
    payload["reference_count"] = len(payload.get("references", []) or [])
    return payload


def patch_summary_payload(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    if overlay.summary is None:
        return payload
    payload["diff_summary"] = overlay.summary
    return payload


def patch_call_neighbors(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    target_id = payload.get("callable_id")
    if not target_id:
        return payload
    callers = {
        entry.get("structural_id"): entry for entry in payload.get("callers", []) or []
    }
    callees = {
        entry.get("structural_id"): entry for entry in payload.get("callees", []) or []
    }
    ids_needed: set[str] = set()
    for change in overlay.calls.get("add", []) + overlay.calls.get("remove", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if src_id == target_id or dst_id == target_id:
            if src_id:
                ids_needed.add(str(src_id))
            if dst_id:
                ids_needed.add(str(dst_id))
    meta_lookup = _node_meta_lookup(conn, snapshot_id, overlay, ids_needed)

    def _entry(node_id: str) -> dict[str, object] | None:
        meta = meta_lookup.get(node_id, {})
        qualified = meta.get("qualified_name")
        node_type = meta.get("node_type")
        if not qualified or not node_type:
            return None
        return {
            "structural_id": node_id,
            "qualified_name": qualified,
            "node_type": node_type,
        }

    for change in overlay.calls.get("add", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if src_id == target_id and dst_id:
            entry = _entry(str(dst_id))
            if entry:
                callees[str(dst_id)] = entry
        if dst_id == target_id and src_id:
            entry = _entry(str(src_id))
            if entry:
                callers[str(src_id)] = entry
    for change in overlay.calls.get("remove", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if src_id == target_id and dst_id:
            callees.pop(str(dst_id), None)
        if dst_id == target_id and src_id:
            callers.pop(str(src_id), None)

    payload["callers"] = sorted(
        callers.values(), key=lambda item: str(item.get("qualified_name"))
    )
    payload["callees"] = sorted(
        callees.values(), key=lambda item: str(item.get("qualified_name"))
    )
    payload["caller_count"] = len(payload["callers"])
    payload["callee_count"] = len(payload["callees"])
    return payload


def patch_callsite_index(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    target_id = payload.get("callable_id")
    if not target_id:
        return payload
    direction = str(payload.get("direction") or "both").lower()
    edges = list(payload.get("edges", []) or [])
    edge_map: dict[tuple[str, str, str], dict[str, object]] = {}
    for entry in edges:
        key = (
            str(entry.get("caller_id") or ""),
            str(entry.get("callee_id") or ""),
            str(entry.get("edge_kind") or "CALLS"),
        )
        edge_map[key] = entry
    ids_needed: set[str] = set()
    for change in overlay.calls.get("add", []) + overlay.calls.get("remove", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if src_id:
            ids_needed.add(str(src_id))
        if dst_id:
            ids_needed.add(str(dst_id))
    meta_lookup = _node_meta_lookup(conn, snapshot_id, overlay, ids_needed)

    def _module_name(node_id: str) -> str | None:
        meta = meta_lookup.get(node_id, {})
        return _module_for_node(
            str(meta.get("node_type") or ""), str(meta.get("qualified_name") or "")
        )

    def _entry(caller_id: str, callee_id: str, edge_source: str) -> dict[str, object]:
        caller = meta_lookup.get(caller_id, {})
        callee = meta_lookup.get(callee_id, {})
        return {
            "caller_id": caller_id,
            "callee_id": callee_id,
            "caller_qualified_name": caller.get("qualified_name"),
            "callee_qualified_name": callee.get("qualified_name"),
            "caller_file_path": caller.get("file_path"),
            "callee_file_path": callee.get("file_path"),
            "caller_language": caller.get("language"),
            "callee_language": callee.get("language"),
            "caller_node_type": caller.get("node_type"),
            "callee_node_type": callee.get("node_type"),
            "caller_module_qualified_name": _module_name(caller_id),
            "callee_module_qualified_name": _module_name(callee_id),
            "edge_kind": "CALLS",
            "edge_source": edge_source,
            "call_hash": None,
            "line_span": None,
        }

    def _matches_direction(src_id: str, dst_id: str) -> bool:
        if direction == "out":
            return src_id == target_id
        if direction == "in":
            return dst_id == target_id
        return src_id == target_id or dst_id == target_id

    for change in overlay.calls.get("add", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if not src_id or not dst_id:
            continue
        if not _matches_direction(str(src_id), str(dst_id)):
            continue
        key = (str(src_id), str(dst_id), "CALLS")
        edge_map[key] = _entry(str(src_id), str(dst_id), "overlay")

    for change in overlay.calls.get("remove", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if not src_id or not dst_id:
            continue
        if not _matches_direction(str(src_id), str(dst_id)):
            continue
        edge_map.pop((str(src_id), str(dst_id), "CALLS"), None)

    payload["edges"] = sorted(
        edge_map.values(),
        key=lambda item: (
            str(item.get("caller_id")),
            str(item.get("callee_id")),
        ),
    )
    payload["edge_count"] = len(payload["edges"])
    return payload


def patch_module_call_graph_summary(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    target_id = payload.get("module_qualified_name")
    if not target_id:
        return payload
    top_k = payload.get("top_k")
    outgoing_map: dict[tuple[str, str], int] = {}
    incoming_map: dict[tuple[str, str], int] = {}
    for entry in payload.get("outgoing", []) or []:
        key = (
            str(entry.get("src_module_qualified_name")),
            str(entry.get("dst_module_qualified_name")),
        )
        outgoing_map[key] = int(entry.get("call_count") or 0)
    for entry in payload.get("incoming", []) or []:
        key = (
            str(entry.get("src_module_qualified_name")),
            str(entry.get("dst_module_qualified_name")),
        )
        incoming_map[key] = int(entry.get("call_count") or 0)
    ids_needed: set[str] = set()
    for change in overlay.calls.get("add", []) + overlay.calls.get("remove", []):
        if change.get("src_structural_id"):
            ids_needed.add(str(change.get("src_structural_id")))
        if change.get("dst_structural_id"):
            ids_needed.add(str(change.get("dst_structural_id")))
    meta_lookup = _node_meta_lookup(conn, snapshot_id, overlay, ids_needed)

    def _module_id(node_id: str) -> str | None:
        meta = meta_lookup.get(node_id, {})
        module_name = _module_for_node(
            str(meta.get("node_type") or ""), str(meta.get("qualified_name") or "")
        )
        language = meta.get("language")
        if not module_name or not language:
            return None
        return ids.structural_id("module", str(language), str(module_name))

    for change in overlay.calls.get("add", []) + overlay.calls.get("remove", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if not src_id or not dst_id:
            continue
        src_module = _module_id(str(src_id))
        dst_module = _module_id(str(dst_id))
        if not src_module or not dst_module:
            continue
        delta = 1 if change.get("diff_kind") == "add" else -1
        if src_module == target_id:
            outgoing_map[(src_module, dst_module)] = max(
                0, outgoing_map.get((src_module, dst_module), 0) + delta
            )
        if dst_module == target_id:
            incoming_map[(src_module, dst_module)] = max(
                0, incoming_map.get((src_module, dst_module), 0) + delta
            )

    def _entries(edge_map: dict[tuple[str, str], int], direction: str) -> list[dict[str, object]]:
        entries = []
        for (src, dst), count in edge_map.items():
            if count <= 0:
                continue
            entries.append(
                {
                    "src_module_qualified_name": src,
                    "dst_module_qualified_name": dst,
                    "direction": direction,
                    "call_count": count,
                }
            )
        entries.sort(
            key=lambda item: (
                -int(item.get("call_count") or 0),
                str(item.get("src_module_qualified_name")),
                str(item.get("dst_module_qualified_name")),
            )
        )
        if top_k is not None:
            try:
                limit = int(top_k)
            except (TypeError, ValueError):
                limit = None
            if limit and limit > 0:
                entries = entries[:limit]
        return entries

    outgoing_all = _entries(outgoing_map, "outgoing")
    incoming_all = _entries(incoming_map, "incoming")
    payload["outgoing"] = outgoing_all
    payload["incoming"] = incoming_all
    payload["outgoing_count"] = len(outgoing_all)
    payload["incoming_count"] = len(incoming_all)
    payload["outgoing_total"] = len(outgoing_all)
    payload["incoming_total"] = len(incoming_all)
    payload["total_edges"] = len(outgoing_all) + len(incoming_all)
    payload["edge_summary"] = {
        "CALLS": {"outgoing": len(outgoing_all), "incoming": len(incoming_all)}
    }
    if outgoing_all:
        payload["outgoing_coverage_ratio"] = 1.0
    if incoming_all:
        payload["incoming_coverage_ratio"] = 1.0
    return payload


def patch_class_call_graph_summary(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    target_id = payload.get("class_id")
    if not target_id:
        return payload
    top_k = payload.get("top_k")
    outgoing_map: dict[tuple[str, str], int] = {}
    incoming_map: dict[tuple[str, str], int] = {}
    for entry in payload.get("outgoing", []) or []:
        key = (str(entry.get("src_class_id")), str(entry.get("dst_class_id")))
        outgoing_map[key] = int(entry.get("call_count") or 0)
    for entry in payload.get("incoming", []) or []:
        key = (str(entry.get("src_class_id")), str(entry.get("dst_class_id")))
        incoming_map[key] = int(entry.get("call_count") or 0)
    ids_needed: set[str] = set()
    for change in overlay.calls.get("add", []) + overlay.calls.get("remove", []):
        if change.get("src_structural_id"):
            ids_needed.add(str(change.get("src_structural_id")))
        if change.get("dst_structural_id"):
            ids_needed.add(str(change.get("dst_structural_id")))
    meta_lookup = _node_meta_lookup(conn, snapshot_id, overlay, ids_needed)

    def _class_id(node_id: str) -> str | None:
        meta = meta_lookup.get(node_id, {})
        if meta.get("node_type") != "method":
            return None
        qualified = str(meta.get("qualified_name") or "")
        language = meta.get("language")
        parts = qualified.split(".")
        if len(parts) < 2 or not language:
            return None
        class_name = ".".join(parts[:-1])
        return ids.structural_id("class", str(language), class_name)

    for change in overlay.calls.get("add", []) + overlay.calls.get("remove", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if not src_id or not dst_id:
            continue
        src_class = _class_id(str(src_id))
        dst_class = _class_id(str(dst_id))
        if not src_class or not dst_class:
            continue
        delta = 1 if change.get("diff_kind") == "add" else -1
        if src_class == target_id:
            outgoing_map[(src_class, dst_class)] = max(
                0, outgoing_map.get((src_class, dst_class), 0) + delta
            )
        if dst_class == target_id:
            incoming_map[(src_class, dst_class)] = max(
                0, incoming_map.get((src_class, dst_class), 0) + delta
            )

    def _entries(edge_map: dict[tuple[str, str], int], direction: str) -> list[dict[str, object]]:
        entries = []
        for (src, dst), count in edge_map.items():
            if count <= 0:
                continue
            entries.append(
                {
                    "src_class_id": src,
                    "dst_class_id": dst,
                    "direction": direction,
                    "call_count": count,
                }
            )
        entries.sort(
            key=lambda item: (
                -int(item.get("call_count") or 0),
                str(item.get("src_class_id")),
                str(item.get("dst_class_id")),
            )
        )
        if top_k is not None:
            try:
                limit = int(top_k)
            except (TypeError, ValueError):
                limit = None
            if limit and limit > 0:
                entries = entries[:limit]
        return entries

    outgoing_all = _entries(outgoing_map, "outgoing")
    incoming_all = _entries(incoming_map, "incoming")
    payload["outgoing"] = outgoing_all
    payload["incoming"] = incoming_all
    payload["outgoing_count"] = len(outgoing_all)
    payload["incoming_count"] = len(incoming_all)
    payload["outgoing_total"] = len(outgoing_all)
    payload["incoming_total"] = len(incoming_all)
    payload["total_edges"] = len(outgoing_all) + len(incoming_all)
    payload["edge_summary"] = {
        "CALLS": {"outgoing": len(outgoing_all), "incoming": len(incoming_all)}
    }
    if outgoing_all:
        payload["outgoing_coverage_ratio"] = 1.0
    if incoming_all:
        payload["incoming_coverage_ratio"] = 1.0
    return payload


def patch_fan_summary(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    node_id = payload.get("node_id")
    if node_id:
        edge_kinds = dict(payload.get("edge_kinds") or {})
        deltas = _fan_deltas_for_node(overlay, str(node_id))
        for edge_kind, delta_map in deltas.items():
            entry = dict(edge_kinds.get(edge_kind) or {})
            entry["fan_in"] = max(0, int(entry.get("fan_in") or 0) + delta_map.get("fan_in", 0))
            entry["fan_out"] = max(0, int(entry.get("fan_out") or 0) + delta_map.get("fan_out", 0))
            edge_kinds[edge_kind] = entry
        payload["edge_kinds"] = edge_kinds
        payload["edge_summary"] = edge_kinds
        return payload

    calls_table = dict(payload.get("calls") or {})
    imports_table = dict(payload.get("imports") or {})
    payload["calls"] = _patch_fan_table(calls_table, overlay, edge_kind="CALLS")
    payload["imports"] = _patch_fan_table(
        imports_table, overlay, edge_kind="IMPORTS_DECLARED"
    )
    return payload


def patch_hotspot_summary(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    by_size = list(payload.get("by_size", []) or [])
    size_map = {entry.get("module_qualified_name"): int(entry.get("count") or 0) for entry in by_size}
    module_names = [name for name in size_map.keys() if name]
    for change in iter_node_changes(overlay):
        node = node_from_value(change.get("new_value") or change.get("old_value"))
        if not node:
            continue
        node_type = str(node.get("node_type") or "")
        if node_type not in {"class", "function", "method"}:
            continue
        module_name = _match_module_name(
            str(node.get("qualified_name") or ""), module_names
        )
        if module_name not in size_map:
            continue
        delta = 1 if change.get("diff_kind") == "add" else -1 if change.get("diff_kind") == "remove" else 0
        if delta:
            size_map[module_name] = max(0, size_map.get(module_name, 0) + delta)

    by_size = [
        {"module_qualified_name": name, "count": count}
        for name, count in size_map.items()
    ]
    by_size.sort(key=lambda item: (-int(item.get("count") or 0), str(item.get("module_qualified_name"))))
    payload["by_size"] = by_size[: len(payload.get("by_size", []) or [])]

    fan_in = {entry.get("module_qualified_name"): int(entry.get("count") or 0) for entry in payload.get("by_fan_in", []) or []}
    fan_out = {entry.get("module_qualified_name"): int(entry.get("count") or 0) for entry in payload.get("by_fan_out", []) or []}
    for change in iter_edge_changes(overlay):
        edge = edge_from_value(change.get("new_value") or change.get("old_value"))
        if not edge or edge.get("edge_type") != "IMPORTS_DECLARED":
            continue
        src_name = edge.get("src_qualified_name")
        dst_name = edge.get("dst_qualified_name")
        delta = 1 if change.get("diff_kind") == "add" else -1 if change.get("diff_kind") == "remove" else 0
        if delta:
            if src_name in fan_out:
                fan_out[src_name] = max(0, fan_out.get(src_name, 0) + delta)
            if dst_name in fan_in:
                fan_in[dst_name] = max(0, fan_in.get(dst_name, 0) + delta)
    payload["by_fan_in"] = [
        {"module_qualified_name": name, "count": count}
        for name, count in sorted(fan_in.items(), key=lambda item: (-item[1], str(item[0])))
    ][: len(payload.get("by_fan_in", []) or [])]
    payload["by_fan_out"] = [
        {"module_qualified_name": name, "count": count}
        for name, count in sorted(fan_out.items(), key=lambda item: (-item[1], str(item[0])))
    ][: len(payload.get("by_fan_out", []) or [])]
    return payload


def _node_meta_lookup(
    conn,
    snapshot_id: str,
    overlay: OverlayPayload,
    node_ids: set[str],
) -> dict[str, dict[str, object]]:
    lookup: dict[str, dict[str, object]] = {}
    for change in iter_node_changes(overlay):
        node = node_from_value(change.get("new_value") or change.get("old_value"))
        if not node:
            continue
        structural_id = node.get("structural_id")
        if not structural_id:
            continue
        lookup[str(structural_id)] = {
            "qualified_name": node.get("qualified_name"),
            "file_path": node.get("file_path"),
            "node_type": node.get("node_type"),
            "language": node.get("language"),
        }
    if not node_ids:
        return lookup
    missing = [node_id for node_id in node_ids if node_id not in lookup]
    if not missing:
        return lookup
    placeholders = ",".join("?" for _ in missing)
    rows = conn.execute(
        f"""
        SELECT sn.structural_id, sn.node_type, sn.language, ni.qualified_name, ni.file_path
        FROM structural_nodes sn
        JOIN node_instances ni
            ON ni.structural_id = sn.structural_id
           AND ni.snapshot_id = ?
        WHERE sn.structural_id IN ({placeholders})
        """,
        (snapshot_id, *missing),
    ).fetchall()
    for row in rows:
        lookup[str(row["structural_id"])] = {
            "qualified_name": row["qualified_name"],
            "file_path": row["file_path"],
            "node_type": row["node_type"],
            "language": row["language"],
        }
    return lookup


def _module_for_node(node_type: str, qualified_name: str) -> str | None:
    if not qualified_name:
        return None
    if node_type == "module":
        return qualified_name
    parts = qualified_name.split(".")
    if not parts:
        return None
    if node_type == "method":
        if len(parts) >= 3:
            return ".".join(parts[:-2])
        return None
    if len(parts) >= 2:
        return ".".join(parts[:-1])
    return None


def _match_module_name(qualified_name: str, module_names: list[str]) -> str | None:
    if not qualified_name or not module_names:
        return None
    best = None
    best_len = -1
    q_parts = qualified_name.split(".")
    for name in module_names:
        n_parts = name.split(".")
        if len(n_parts) > len(q_parts):
            continue
        for idx in range(len(q_parts) - len(n_parts) + 1):
            if q_parts[idx : idx + len(n_parts)] == n_parts:
                if len(n_parts) > best_len:
                    best = name
                    best_len = len(n_parts)
                break
    return best


def _fan_deltas_for_node(overlay: OverlayPayload, node_id: str) -> dict[str, dict[str, int]]:
    deltas: dict[str, dict[str, int]] = {
        "CALLS": {"fan_in": 0, "fan_out": 0},
        "IMPORTS_DECLARED": {"fan_in": 0, "fan_out": 0},
    }
    for change in overlay.calls.get("add", []):
        if change.get("src_structural_id") == node_id:
            deltas["CALLS"]["fan_out"] += 1
        if change.get("dst_structural_id") == node_id:
            deltas["CALLS"]["fan_in"] += 1
    for change in overlay.calls.get("remove", []):
        if change.get("src_structural_id") == node_id:
            deltas["CALLS"]["fan_out"] -= 1
        if change.get("dst_structural_id") == node_id:
            deltas["CALLS"]["fan_in"] -= 1
    for change in overlay.edges.get("add", []):
        edge = edge_from_value(change.get("new_value") or change.get("old_value"))
        if not edge or edge.get("edge_type") != "IMPORTS_DECLARED":
            continue
        if edge.get("src_structural_id") == node_id:
            deltas["IMPORTS_DECLARED"]["fan_out"] += 1
        if edge.get("dst_structural_id") == node_id:
            deltas["IMPORTS_DECLARED"]["fan_in"] += 1
    for change in overlay.edges.get("remove", []):
        edge = edge_from_value(change.get("new_value") or change.get("old_value"))
        if not edge or edge.get("edge_type") != "IMPORTS_DECLARED":
            continue
        if edge.get("src_structural_id") == node_id:
            deltas["IMPORTS_DECLARED"]["fan_out"] -= 1
        if edge.get("dst_structural_id") == node_id:
            deltas["IMPORTS_DECLARED"]["fan_in"] -= 1
    return deltas


def _patch_fan_table(
    table: dict[str, object],
    overlay: OverlayPayload,
    *,
    edge_kind: str,
) -> dict[str, object]:
    by_in = {entry.get("node_id"): int(entry.get("count") or 0) for entry in table.get("by_fan_in", []) or []}
    by_out = {entry.get("node_id"): int(entry.get("count") or 0) for entry in table.get("by_fan_out", []) or []}
    if edge_kind == "CALLS":
        for change in overlay.calls.get("add", []) + overlay.calls.get("remove", []):
            delta = 1 if change.get("diff_kind") == "add" else -1
            src_id = change.get("src_structural_id")
            dst_id = change.get("dst_structural_id")
            if src_id in by_out:
                by_out[src_id] = max(0, by_out.get(src_id, 0) + delta)
            if dst_id in by_in:
                by_in[dst_id] = max(0, by_in.get(dst_id, 0) + delta)
    if edge_kind == "IMPORTS_DECLARED":
        for change in overlay.edges.get("add", []) + overlay.edges.get("remove", []):
            edge = edge_from_value(change.get("new_value") or change.get("old_value"))
            if not edge or edge.get("edge_type") != "IMPORTS_DECLARED":
                continue
            delta = 1 if change.get("diff_kind") == "add" else -1
            src_id = edge.get("src_structural_id")
            dst_id = edge.get("dst_structural_id")
            if src_id in by_out:
                by_out[src_id] = max(0, by_out.get(src_id, 0) + delta)
            if dst_id in by_in:
                by_in[dst_id] = max(0, by_in.get(dst_id, 0) + delta)
    table["by_fan_in"] = [
        {"node_id": node_id, "count": count}
        for node_id, count in sorted(by_in.items(), key=lambda item: (-item[1], str(item[0])))
    ]
    table["by_fan_out"] = [
        {"node_id": node_id, "count": count}
        for node_id, count in sorted(by_out.items(), key=lambda item: (-item[1], str(item[0])))
    ]
    return table


def parse_json_fenced(text: str) -> Optional[dict[str, object]]:
    stripped = text.strip()
    if not stripped.startswith("```json"):
        return None
    start = stripped.find("\n")
    end = stripped.rfind("```")
    if start == -1 or end == -1 or end <= start:
        return None
    body = stripped[start:end].strip()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


__all__ = [
    "apply_overlay_to_payload",
    "parse_json_fenced",
    "patch_summary_payload",
]
