"""Dirty-worktree diff overlay helpers for reducer payloads."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import pathspec

from ..code_analysis.core.extract import registry
from ..code_analysis import config as analysis_config
from ..code_analysis.core.normalize.model import (
    FileRecord,
    FileSnapshot,
    SemanticNodeRecord,
)
from ..code_analysis.tools import snapshots as snapshot_tools
from ..data_storage.artifact_db import diff_overlay as overlay_store
from ..data_storage.core_db import read_ops as core_read
from ..reducers.helpers.render import render_json_payload
from ..runtime import config as runtime_config
from ..runtime.config import io as runtime_config_io
from ..runtime import constants as runtime_constants
from ..runtime import git as git_ops
from ..runtime.errors import GitError
from ..runtime import identity as ids
from ..runtime import time as runtime_time
from ..runtime.errors import ConfigError


@dataclass(frozen=True)
class OverlayPayload:
    worktree_hash: str
    nodes: dict[str, list[dict[str, object]]]
    edges: dict[str, list[dict[str, object]]]


def get_overlay(
    *,
    repo_root: Path,
    snapshot_id: str,
    core_conn,
    artifact_conn,
) -> Optional[OverlayPayload]:
    if artifact_conn is None:
        return None
    if not git_ops.is_worktree_dirty(repo_root):
        return None
    base_commit = core_read.snapshot_git_commit_sha(core_conn, snapshot_id)
    if not base_commit:
        return None
    try:
        git_ops.run_git(["rev-parse", base_commit], repo_root)
    except GitError:
        base_commit = "HEAD"
    worktree_hash = _worktree_fingerprint(repo_root, base_commit)
    if not overlay_store.overlay_exists(artifact_conn, snapshot_id, worktree_hash):
        rows = _compute_overlay_rows(
            repo_root=repo_root,
            snapshot_id=snapshot_id,
            base_commit=base_commit,
            core_conn=core_conn,
            worktree_hash=worktree_hash,
        )
        overlay_store.insert_overlay_rows(artifact_conn, rows)
        artifact_conn.commit()
    rows = overlay_store.fetch_overlay_rows(artifact_conn, snapshot_id, worktree_hash)
    if not rows:
        return None
    return _rows_to_payload(worktree_hash, rows)


def apply_overlay_to_text(
    text: str,
    overlay: Optional[OverlayPayload],
    *,
    snapshot_id: str,
    conn,
) -> str:
    if not overlay:
        return text
    payload = _parse_json_fenced(text)
    if payload is None:
        return text
    patched = _apply_overlay_to_payload(
        payload, overlay, snapshot_id=snapshot_id, conn=conn
    )
    patched["_diff"] = {
        "worktree_hash": overlay.worktree_hash,
        "nodes": overlay.nodes,
        "edges": overlay.edges,
    }
    return render_json_payload(patched)


def _worktree_fingerprint(repo_root: Path, base_commit: str) -> str:
    parts = []
    parts.append(git_ops.run_git(["diff", "--name-status", base_commit], repo_root))
    parts.append(
        git_ops.run_git(["diff", "--cached", "--name-status", base_commit], repo_root)
    )
    parts.append(
        git_ops.run_git(["ls-files", "--others", "--exclude-standard"], repo_root)
    )
    config_text = runtime_config_io.load_config_text(repo_root) or ""
    parts.append(config_text)
    parts.append(runtime_constants.TOOL_VERSION)
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return digest


def _compute_overlay_rows(
    *,
    repo_root: Path,
    snapshot_id: str,
    base_commit: str,
    core_conn,
    worktree_hash: str,
) -> list[dict[str, object]]:
    change_set = _collect_changes(repo_root, base_commit)
    target_paths = sorted(change_set.changed_paths)
    deleted_paths = sorted(change_set.deleted_paths)
    records = _build_file_records(repo_root, target_paths)
    file_paths = [record.relative_path.as_posix() for record in records]
    snapshot_rows = core_read.node_instances_for_file_paths(
        core_conn, snapshot_id, [*file_paths, *deleted_paths]
    )
    snapshot_nodes = {row["structural_id"]: row for row in snapshot_rows}
    analysis_nodes, analysis_edges = _analyze_files(repo_root, records)
    analysis_map = {node["structural_id"]: node for node in analysis_nodes}
    analysis_src_ids = set(analysis_map.keys())
    snapshot_src_ids = {row["structural_id"] for row in snapshot_rows}

    snapshot_edges = core_read.edges_for_source_ids(
        core_conn, snapshot_id, sorted(snapshot_src_ids)
    )
    analysis_edges_set = {
        (edge["src_structural_id"], edge["dst_structural_id"], edge["edge_type"])
        for edge in analysis_edges
        if edge["src_structural_id"] in analysis_src_ids
    }
    snapshot_edges_set = set(snapshot_edges)

    rows: list[dict[str, object]] = []
    created_at = runtime_time.utc_now()
    for node_id, node in analysis_map.items():
        snapshot_node = snapshot_nodes.get(node_id)
        if not snapshot_node:
            rows.append(
                _overlay_row(
                    snapshot_id,
                    node_id,
                    node["node_type"],
                    diff_kind="add",
                    field="node",
                    new_value=json.dumps(node, sort_keys=True),
                    created_at=created_at,
                    worktree_hash=worktree_hash,
                )
            )
            continue
        for field in (
            "qualified_name",
            "file_path",
            "start_line",
            "end_line",
            "content_hash",
        ):
            old_value = snapshot_node[field]
            new_value = node[field]
            if str(old_value) != str(new_value):
                rows.append(
                    _overlay_row(
                        snapshot_id,
                        node_id,
                        node["node_type"],
                        diff_kind="modify",
                        field=field,
                        old_value=str(old_value),
                        new_value=str(new_value),
                        created_at=created_at,
                        worktree_hash=worktree_hash,
                    )
                )

    for node_id, snapshot_node in snapshot_nodes.items():
        if node_id in analysis_map:
            continue
        rows.append(
            _overlay_row(
                snapshot_id,
                node_id,
                snapshot_node["node_type"],
                diff_kind="remove",
                field="node",
                old_value=json.dumps(snapshot_node, sort_keys=True),
                created_at=created_at,
                worktree_hash=worktree_hash,
            )
        )

    node_lookup = _build_node_lookup(snapshot_nodes, analysis_map)
    for src_id, dst_id, edge_type in analysis_edges_set - snapshot_edges_set:
        src_meta = node_lookup.get(src_id, {})
        dst_meta = node_lookup.get(dst_id, {})
        rows.append(
            _overlay_row(
                snapshot_id,
                _edge_key(src_id, dst_id, edge_type),
                "edge",
                diff_kind="add",
                field="edge",
                new_value=json.dumps(
                    {
                        "src_structural_id": src_id,
                        "dst_structural_id": dst_id,
                        "edge_type": edge_type,
                        "src_qualified_name": src_meta.get("qualified_name"),
                        "dst_qualified_name": dst_meta.get("qualified_name"),
                        "src_file_path": src_meta.get("file_path"),
                        "dst_file_path": dst_meta.get("file_path"),
                    },
                    sort_keys=True,
                ),
                created_at=created_at,
                worktree_hash=worktree_hash,
            )
        )
    for src_id, dst_id, edge_type in snapshot_edges_set - analysis_edges_set:
        src_meta = node_lookup.get(src_id, {})
        dst_meta = node_lookup.get(dst_id, {})
        rows.append(
            _overlay_row(
                snapshot_id,
                _edge_key(src_id, dst_id, edge_type),
                "edge",
                diff_kind="remove",
                field="edge",
                old_value=json.dumps(
                    {
                        "src_structural_id": src_id,
                        "dst_structural_id": dst_id,
                        "edge_type": edge_type,
                        "src_qualified_name": src_meta.get("qualified_name"),
                        "dst_qualified_name": dst_meta.get("qualified_name"),
                        "src_file_path": src_meta.get("file_path"),
                        "dst_file_path": dst_meta.get("file_path"),
                    },
                    sort_keys=True,
                ),
                created_at=created_at,
                worktree_hash=worktree_hash,
            )
        )
    return rows


def _rows_to_payload(
    worktree_hash: str, rows: Iterable[dict[str, object]]
) -> OverlayPayload:
    nodes = {"add": [], "remove": [], "modify": []}
    edges = {"add": [], "remove": []}
    for row in rows:
        node_type = row["node_type"]
        diff_kind = row["diff_kind"]
        entry = {
            "structural_id": row["structural_id"],
            "field": row.get("field"),
            "old_value": row.get("old_value"),
            "new_value": row.get("new_value"),
        }
        if node_type == "edge":
            if diff_kind in edges:
                edges[diff_kind].append(entry)
            continue
        if diff_kind in nodes:
            nodes[diff_kind].append(entry)
    return OverlayPayload(worktree_hash=worktree_hash, nodes=nodes, edges=edges)


def _build_node_lookup(
    snapshot_nodes: dict[str, dict[str, object]],
    analysis_nodes: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    lookup: dict[str, dict[str, object]] = {}
    for structural_id, row in snapshot_nodes.items():
        lookup[structural_id] = {
            "qualified_name": row.get("qualified_name"),
            "file_path": row.get("file_path"),
        }
    for structural_id, row in analysis_nodes.items():
        lookup[structural_id] = {
            "qualified_name": row.get("qualified_name"),
            "file_path": row.get("file_path"),
        }
    return lookup


def _apply_overlay_to_payload(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    projection = str(payload.get("projection", "")).strip().lower()
    if projection == "structural_index":
        return _patch_structural_index(payload, overlay)
    if projection == "module_overview":
        return _patch_module_overview(payload, overlay)
    if projection == "callable_overview":
        return _patch_callable_overview(payload, overlay)
    if projection == "class_overview":
        return _patch_class_overview(payload, overlay)
    if projection == "file_outline":
        return _patch_file_outline(payload, overlay)
    if projection == "module_file_map":
        return _patch_module_file_map(payload, overlay)
    if projection == "dependency_edges":
        return _patch_dependency_edges(payload, overlay)
    if projection == "import_references":
        return _patch_import_references(payload, overlay)
    if projection == "importers_index":
        return _patch_importers_index(payload, overlay)
    if projection == "symbol_lookup":
        return _patch_symbol_lookup(payload, overlay)
    if projection == "symbol_references":
        return _patch_symbol_references(payload, overlay)
    return payload


def _iter_node_changes(overlay: OverlayPayload) -> list[dict[str, object]]:
    changes: list[dict[str, object]] = []
    for diff_kind, entries in overlay.nodes.items():
        for entry in entries:
            record = dict(entry)
            record["diff_kind"] = diff_kind
            changes.append(record)
    return changes


def _iter_edge_changes(overlay: OverlayPayload) -> list[dict[str, object]]:
    changes: list[dict[str, object]] = []
    for diff_kind, entries in overlay.edges.items():
        for entry in entries:
            record = dict(entry)
            record["diff_kind"] = diff_kind
            changes.append(record)
    return changes


def _node_from_value(value: str | None) -> Optional[dict[str, object]]:
    if not value:
        return None
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    return decoded


def _edge_from_value(value: str | None) -> Optional[dict[str, object]]:
    if not value:
        return None
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    return decoded


def _module_for_node(node_type: str, qualified_name: str) -> Optional[str]:
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


def _module_in_scope(module_name: str, target: str) -> bool:
    if module_name == target:
        return True
    return target.startswith(f"{module_name}.")


def _patch_structural_index(
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

    for change in _iter_node_changes(overlay):
        node = _node_from_value(change.get("new_value") or change.get("old_value"))
        if not node:
            continue
        node_type = str(node.get("node_type", ""))
        qualified_name = str(node.get("qualified_name", ""))
        module_name = _module_for_node(node_type, qualified_name)
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
    for change in _iter_edge_changes(overlay):
        edge = _edge_from_value(change.get("new_value") or change.get("old_value"))
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


def _patch_module_overview(
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

    for change in _iter_node_changes(overlay):
        node = _node_from_value(change.get("new_value") or change.get("old_value"))
        if not node:
            continue
        node_type = str(node.get("node_type", ""))
        qualified_name = str(node.get("qualified_name", ""))
        node_module = _module_for_node(node_type, qualified_name)
        if not node_module or not _module_in_scope(module_name, node_module):
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

    for change in _iter_edge_changes(overlay):
        edge = _edge_from_value(change.get("new_value") or change.get("old_value"))
        if not edge or edge.get("edge_type") != "IMPORTS_DECLARED":
            continue
        src_name = edge.get("src_qualified_name")
        if not src_name or not _module_in_scope(module_name, str(src_name)):
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


def _patch_callable_overview(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    structural_id = payload.get("function_id") or payload.get("callable_id")
    if not structural_id:
        return payload
    for change in _iter_node_changes(overlay):
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


def _patch_class_overview(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    class_id = payload.get("class_id")
    if not class_id:
        return payload
    methods = list(payload.get("methods", []) or [])
    method_ids = {
        entry.get("function_id") for entry in methods if entry.get("function_id")
    }
    for change in _iter_node_changes(overlay):
        node = _node_from_value(change.get("new_value") or change.get("old_value"))
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
            parent_module = _module_for_node(
                "method", str(node.get("qualified_name", ""))
            )
            if (
                payload.get("module_qualified_name")
                and parent_module
                and not _module_in_scope(
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


def _patch_file_outline(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    files = list(payload.get("files", []) or [])
    file_map = {
        entry.get("file_path"): entry for entry in files if entry.get("file_path")
    }
    file_filter = payload.get("file_path")
    module_filter = payload.get("module_filter")
    for change in _iter_node_changes(overlay):
        node = _node_from_value(change.get("new_value") or change.get("old_value"))
        if not node:
            continue
        file_path = node.get("file_path")
        if not file_path:
            continue
        if file_filter and file_path != file_filter:
            continue
        qualified_name = str(node.get("qualified_name", ""))
        node_type = str(node.get("node_type", ""))
        module_name = _module_for_node(node_type, qualified_name)
        if (
            module_filter
            and module_name
            and not _module_in_scope(str(module_filter), module_name)
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


def _patch_module_file_map(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    modules = list(payload.get("modules", []) or [])
    module_map = {
        entry.get("module_structural_id"): entry
        for entry in modules
        if entry.get("module_structural_id")
    }
    module_filter = payload.get("module_filter")
    for change in _iter_node_changes(overlay):
        node = _node_from_value(change.get("new_value") or change.get("old_value"))
        if not node or node.get("node_type") != "module":
            continue
        module_name = node.get("qualified_name")
        if (
            module_filter
            and module_name
            and not _module_in_scope(str(module_filter), str(module_name))
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


def _patch_dependency_edges(
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
    for change in _iter_edge_changes(overlay):
        edge = _edge_from_value(change.get("new_value") or change.get("old_value"))
        if not edge or edge.get("edge_type") != "IMPORTS_DECLARED":
            continue
        src_id = edge.get("src_structural_id")
        dst_id = edge.get("dst_structural_id")
        if (
            from_filter
            and edge.get("src_qualified_name")
            and not _module_in_scope(
                str(from_filter), str(edge.get("src_qualified_name"))
            )
        ):
            continue
        if (
            to_filter
            and edge.get("dst_qualified_name")
            and not _module_in_scope(
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


def _patch_import_references(
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
    for change in _iter_edge_changes(overlay):
        edge = _edge_from_value(change.get("new_value") or change.get("old_value"))
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


def _patch_importers_index(
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
    for change in _iter_edge_changes(overlay):
        edge = _edge_from_value(change.get("new_value") or change.get("old_value"))
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


def _patch_symbol_lookup(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    matches = list(payload.get("matches", []) or [])
    match_ids = {
        entry.get("structural_id") for entry in matches if entry.get("structural_id")
    }
    for change in _iter_node_changes(overlay):
        node = _node_from_value(change.get("new_value") or change.get("old_value"))
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


def _patch_symbol_references(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    matches = list(payload.get("matches", []) or [])
    match_ids = {
        entry.get("structural_id") for entry in matches if entry.get("structural_id")
    }
    for change in _iter_node_changes(overlay):
        node = _node_from_value(change.get("new_value") or change.get("old_value"))
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


def _parse_json_fenced(text: str) -> Optional[dict[str, object]]:
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


def _collect_changes(repo_root: Path, base_commit: str) -> "_ChangeSet":
    added: set[str] = set()
    modified: set[str] = set()
    deleted: set[str] = set()
    for status, paths in git_ops.diff_name_status(repo_root, base_commit):
        _ingest_status(status, paths, added, modified, deleted)
    for status, paths in git_ops.diff_name_status(repo_root, base_commit, cached=True):
        _ingest_status(status, paths, added, modified, deleted)
    for path in git_ops.untracked_paths(repo_root):
        added.add(path)
    changed_paths = sorted(added | modified)
    deleted_paths = sorted(deleted)
    return _ChangeSet(changed_paths=changed_paths, deleted_paths=deleted_paths)


def _ingest_status(
    status: str,
    paths: list[str],
    added: set[str],
    modified: set[str],
    deleted: set[str],
) -> None:
    if status.startswith("R") or status.startswith("C"):
        if len(paths) >= 2:
            deleted.add(paths[0])
            added.add(paths[1])
        return
    if status.startswith("D"):
        deleted.add(paths[0])
        return
    if status.startswith("A"):
        added.add(paths[0])
        return
    modified.add(paths[0])


def _build_file_records(repo_root: Path, paths: list[str]) -> list[FileRecord]:
    enabled_languages = _enabled_languages(repo_root)
    exclude_globs = _discovery_excludes(repo_root)
    exclude_spec = (
        pathspec.PathSpec.from_lines("gitwildmatch", exclude_globs)
        if exclude_globs
        else None
    )
    records: list[FileRecord] = []
    for path_str in paths:
        rel_path = Path(path_str)
        if rel_path.parts and rel_path.parts[0] in {".git", ".sciona"}:
            continue
        if exclude_spec and exclude_spec.match_file(rel_path.as_posix()):
            continue
        extension = rel_path.suffix.lower()
        if not extension:
            continue
        language = registry.language_for_extension(extension, enabled_languages)
        if not language:
            continue
        abs_path = repo_root / rel_path
        if not abs_path.is_file():
            continue
        records.append(
            FileRecord(path=abs_path, relative_path=rel_path, language=language)
        )
    return records


def _analyze_files(
    repo_root: Path,
    records: list[FileRecord],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if not records:
        return [], []
    file_snapshots = snapshot_tools.prepare_file_snapshots(repo_root, records)
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []
    analyzers = _analyzers()
    for file_snapshot in file_snapshots:
        analyzer = registry.get_analyzer_for_path(file_snapshot.record.path, analyzers)
        if not analyzer:
            continue
        module_name = analyzer.module_name(repo_root, file_snapshot)
        analysis = analyzer.analyze(file_snapshot, module_name)
        for node in analysis.nodes:
            nodes.append(_node_payload(node, file_snapshot))
        for edge in analysis.edges:
            edges.append(_edge_payload(edge))
    return nodes, edges


def _node_payload(
    node: SemanticNodeRecord, file_snapshot: FileSnapshot
) -> dict[str, object]:
    structural_id = ids.structural_id(
        node.node_type, node.language, node.qualified_name
    )
    return {
        "structural_id": structural_id,
        "node_type": node.node_type,
        "language": node.language,
        "qualified_name": node.qualified_name,
        "file_path": node.file_path.as_posix(),
        "start_line": node.start_line,
        "end_line": node.end_line,
        "content_hash": _node_content_hash(node, file_snapshot),
    }


def _node_content_hash(node: SemanticNodeRecord, file_snapshot: FileSnapshot) -> str:
    content = file_snapshot.content
    if (
        node.start_byte is not None
        and node.end_byte is not None
        and 0 <= node.start_byte <= node.end_byte
        and node.end_byte <= len(content)
    ):
        segment = content[node.start_byte : node.end_byte]
        if segment:
            return hashlib.sha1(segment).hexdigest()
    return file_snapshot.blob_sha


def _edge_payload(edge) -> dict[str, object]:
    src_id = ids.structural_id(
        edge.src_node_type, edge.src_language, edge.src_qualified_name
    )
    dst_id = ids.structural_id(
        edge.dst_node_type, edge.dst_language, edge.dst_qualified_name
    )
    return {
        "src_structural_id": src_id,
        "dst_structural_id": dst_id,
        "edge_type": edge.edge_type,
    }


def _edge_key(src_id: str, dst_id: str, edge_type: str) -> str:
    return hashlib.sha1(f"{src_id}:{dst_id}:{edge_type}".encode("utf-8")).hexdigest()


def _overlay_row(
    snapshot_id: str,
    structural_id: str,
    node_type: str,
    *,
    diff_kind: str,
    created_at: str,
    worktree_hash: str,
    field: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
) -> dict[str, object]:
    return {
        "snapshot_id": snapshot_id,
        "worktree_hash": worktree_hash,
        "structural_id": structural_id,
        "node_type": node_type,
        "diff_kind": diff_kind,
        "field": field,
        "old_value": old_value,
        "new_value": new_value,
        "created_at": created_at,
    }


def _enabled_languages(repo_root: Path) -> list[str]:
    try:
        settings = runtime_config.load_language_settings(repo_root)
        enabled = [name for name, config in settings.items() if config.enabled]
        if enabled:
            return enabled
        return sorted(analysis_config.LANGUAGE_CONFIG.keys())
    except ConfigError:
        return sorted(analysis_config.LANGUAGE_CONFIG.keys())


def _discovery_excludes(repo_root: Path) -> list[str]:
    try:
        return list(runtime_config.load_discovery_settings(repo_root).exclude_globs)
    except ConfigError:
        return []


def _analyzers() -> dict[str, object]:
    analyzers: dict[str, object] = {}
    for language in analysis_config.LANGUAGE_CONFIG.keys():
        analyzer = registry.get_analyzer(language)
        if analyzer:
            analyzers[language] = analyzer
    return analyzers


@dataclass(frozen=True)
class _ChangeSet:
    changed_paths: list[str]
    deleted_paths: list[str]
