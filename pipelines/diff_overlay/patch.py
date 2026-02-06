"""Overlay patching for reducer payloads."""

from __future__ import annotations

import json
from typing import Optional

from .types import OverlayPayload


def apply_overlay_to_payload(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> tuple[dict[str, object], bool]:
    projection = str(payload.get("projection", "")).strip().lower()
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
    if projection == "import_references":
        return patch_import_references(payload, overlay), True
    if projection == "importers_index":
        return patch_importers_index(payload, overlay), True
    if projection == "symbol_lookup":
        return patch_symbol_lookup(payload, overlay), True
    if projection == "symbol_references":
        return patch_symbol_references(payload, overlay), True
    if projection in {
        "call_graph",
        "callsite_index",
        "class_call_graph",
        "module_call_graph",
        "fan_summary",
        "hotspot_summary",
    }:
        return patch_summary_payload(payload, overlay), True
    return payload, False


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


def patch_import_references(
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
