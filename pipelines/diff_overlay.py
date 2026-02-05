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
from ..code_analysis.core.normalize.model import FileRecord, FileSnapshot, SemanticNodeRecord
from ..code_analysis.tools import snapshots as snapshot_tools
from ..data_storage.artifact_db import diff_overlay as overlay_store
from ..data_storage.core_db import read_ops as core_read
from ..reducers.helpers.render import render_json_payload
from ..runtime import config as runtime_config
from ..runtime import config_io as runtime_config_io
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
    rows = overlay_store.fetch_overlay_rows(artifact_conn, snapshot_id, worktree_hash)
    if not rows:
        return None
    return _rows_to_payload(worktree_hash, rows)


def apply_overlay_to_text(text: str, overlay: Optional[OverlayPayload]) -> str:
    if not overlay:
        return text
    payload = _parse_json_fenced(text)
    if payload is None:
        return text
    payload["_diff"] = {
        "worktree_hash": overlay.worktree_hash,
        "nodes": overlay.nodes,
        "edges": overlay.edges,
    }
    return render_json_payload(payload)


def _worktree_fingerprint(repo_root: Path, base_commit: str) -> str:
    parts = []
    parts.append(git_ops.run_git(["diff", "--name-status", base_commit], repo_root))
    parts.append(git_ops.run_git(["diff", "--cached", "--name-status", base_commit], repo_root))
    parts.append(git_ops.run_git(["ls-files", "--others", "--exclude-standard"], repo_root))
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
        for field in ("qualified_name", "file_path", "start_line", "end_line", "content_hash"):
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

    for src_id, dst_id, edge_type in analysis_edges_set - snapshot_edges_set:
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
                    },
                    sort_keys=True,
                ),
                created_at=created_at,
                worktree_hash=worktree_hash,
            )
        )
    for src_id, dst_id, edge_type in snapshot_edges_set - analysis_edges_set:
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
                    },
                    sort_keys=True,
                ),
                created_at=created_at,
                worktree_hash=worktree_hash,
            )
        )
    return rows


def _rows_to_payload(worktree_hash: str, rows: Iterable[dict[str, object]]) -> OverlayPayload:
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


def _node_payload(node: SemanticNodeRecord, file_snapshot: FileSnapshot) -> dict[str, object]:
    structural_id = ids.structural_id(node.node_type, node.language, node.qualified_name)
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
    src_id = ids.structural_id(edge.src_node_type, edge.src_language, edge.src_qualified_name)
    dst_id = ids.structural_id(edge.dst_node_type, edge.dst_language, edge.dst_qualified_name)
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
        return [name for name, config in settings.items() if config.enabled]
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
