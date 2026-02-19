# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Overlay computation helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from collections import Counter
from typing import Iterable

from ...code_analysis.core.extract import registry
from ...code_analysis import config as analysis_config
from ...code_analysis.core.normalize.model import FileRecord, FileSnapshot, SemanticNodeRecord
from ...code_analysis.tools import snapshots as snapshot_tools
from ...code_analysis.tools import excludes as path_excludes
from ...data_storage.core_db import read_ops as core_read
from ...runtime import config as runtime_config
from ...runtime.config import io as runtime_config_io
from ...runtime import constants as runtime_constants
from ...runtime import git as git_ops
from ...runtime import identity as ids
from ...runtime.text import canonical_span_bytes
from ...runtime import time as runtime_time
from ...runtime.errors import ConfigError
from ...runtime.logging import get_logger

from .calls import compute_call_overlay_rows

logger = get_logger(__name__)


def summarize_overlay(
    rows: Iterable[dict[str, object]],
    call_rows: Iterable[dict[str, object]],
) -> dict[str, object] | None:
    node_counts = Counter()
    node_type_counts: dict[str, Counter] = {}
    edge_counts = Counter()
    edge_type_counts: dict[str, Counter] = {}
    for row in rows:
        node_type = row.get("node_type")
        diff_kind = row.get("diff_kind")
        if node_type == "edge":
            edge_counts[diff_kind] += 1
            edge_type = None
            edge_value_raw = row.get("new_value") or row.get("old_value")
            if edge_value_raw:
                try:
                    edge_value = json.loads(edge_value_raw)
                    edge_type = edge_value.get("edge_type")
                except Exception:
                    edge_type = None
            if edge_type:
                edge_type_counts.setdefault(edge_type, Counter())[diff_kind] += 1
            continue
        node_counts[diff_kind] += 1
        if node_type:
            node_type_counts.setdefault(str(node_type), Counter())[diff_kind] += 1

    call_counts = Counter()
    for row in call_rows:
        diff_kind = row.get("diff_kind")
        call_counts[diff_kind] += 1

    def _counter_payload(counter: Counter) -> dict[str, int]:
        return {
            "add": int(counter.get("add", 0)),
            "modify": int(counter.get("modify", 0)),
            "remove": int(counter.get("remove", 0)),
        }

    summary = {
        "nodes": {
            "total": _counter_payload(node_counts),
            "by_type": {
                node_type: _counter_payload(counts)
                for node_type, counts in sorted(node_type_counts.items())
            },
        },
        "edges": {
            "total": {
                "add": int(edge_counts.get("add", 0)),
                "remove": int(edge_counts.get("remove", 0)),
            },
            "by_type": {
                edge_type: {
                    "add": int(counts.get("add", 0)),
                    "remove": int(counts.get("remove", 0)),
                }
                for edge_type, counts in sorted(edge_type_counts.items())
            },
        },
        "calls": {
            "add": int(call_counts.get("add", 0)),
            "remove": int(call_counts.get("remove", 0)),
        },
    }
    if (
        summary["nodes"]["total"] == {"add": 0, "modify": 0, "remove": 0}
        and summary["edges"]["total"] == {"add": 0, "remove": 0}
        and summary["calls"] == {"add": 0, "remove": 0}
    ):
        return None
    return summary

def worktree_fingerprint(
    repo_root: Path,
    base_commit: str,
    *,
    cache: dict[tuple[Path, tuple[str, ...], str | None], str],
) -> str:
    parts = []
    parts.append(
        git_ops.git_output(
            repo_root,
            ["diff", "--name-status", base_commit],
            cache=cache,
        )
    )
    parts.append(
        git_ops.git_output(
            repo_root,
            ["diff", "--cached", "--name-status", base_commit],
            cache=cache,
        )
    )
    parts.append(
        git_ops.git_output(
            repo_root,
            ["ls-files", "--others", "--exclude-standard"],
            cache=cache,
        )
    )
    config_text = runtime_config_io.load_config_text(repo_root) or ""
    parts.append(config_text)
    parts.append(runtime_constants.TOOL_VERSION)
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return digest


def compute_overlay_rows(
    *,
    repo_root: Path,
    snapshot_id: str,
    base_commit: str,
    core_conn,
    artifact_conn,
    worktree_hash: str,
    git_cache: dict[tuple[Path, tuple[str, ...], str | None], str],
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, object] | None,
    list[str],
]:
    change_set = collect_changes(repo_root, base_commit, cache=git_cache)
    exclude_globs = discovery_excludes(repo_root)
    ignored_paths = git_ops.ignored_tracked_paths(repo_root, cache=git_cache)
    target_paths = filter_excluded_paths(
        change_set.changed_paths,
        repo_root=repo_root,
        exclude_globs=exclude_globs,
        ignored_paths=ignored_paths,
    )
    deleted_paths = filter_excluded_paths(
        change_set.deleted_paths,
        repo_root=repo_root,
        exclude_globs=exclude_globs,
        ignored_paths=ignored_paths,
    )
    records = build_file_records(
        repo_root,
        target_paths,
        exclude_globs=exclude_globs,
        ignored_paths=ignored_paths,
    )
    file_paths = [record.relative_path.as_posix() for record in records]
    snapshot_rows = core_read.node_instances_for_file_paths(
        core_conn, snapshot_id, [*file_paths, *deleted_paths]
    )
    snapshot_nodes = {row["structural_id"]: row for row in snapshot_rows}
    analysis_nodes, analysis_edges, analysis_calls = analyze_files(repo_root, records)
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
                overlay_row(
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
                    overlay_row(
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
            overlay_row(
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

    node_lookup = build_node_lookup(snapshot_nodes, analysis_map)
    for src_id, dst_id, edge_type in analysis_edges_set - snapshot_edges_set:
        src_meta = node_lookup.get(src_id, {})
        dst_meta = node_lookup.get(dst_id, {})
        rows.append(
            overlay_row(
                snapshot_id,
                edge_key(src_id, dst_id, edge_type),
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
            overlay_row(
                snapshot_id,
                edge_key(src_id, dst_id, edge_type),
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

    call_rows = compute_call_overlay_rows(
        snapshot_id=snapshot_id,
        worktree_hash=worktree_hash,
        created_at=created_at,
        core_conn=core_conn,
        artifact_conn=artifact_conn,
        analysis_nodes=analysis_nodes,
        analysis_calls=analysis_calls,
        repo_root=repo_root,
    )
    summary = summarize_overlay(rows, call_rows)
    return rows, call_rows, summary, change_set.warnings


def build_node_lookup(
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


def collect_changes(
    repo_root: Path,
    base_commit: str,
    *,
    cache: dict[tuple[Path, tuple[str, ...], str | None], str],
) -> "_ChangeSet":
    submodules = git_ops.submodule_paths(repo_root, cache=cache)
    warnings: list[str] = []
    added: set[str] = set()
    modified: set[str] = set()
    deleted: set[str] = set()
    for status, paths in git_ops.diff_name_status(
        repo_root,
        base_commit,
        cache=cache,
    ):
        ingest_status(status, paths, added, modified, deleted)
    for path in git_ops.untracked_paths(repo_root, cache=cache):
        added.add(path)
    if submodules:
        ignored = sorted(
            path for path in added | modified | deleted if path in submodules
        )
        if ignored:
            logger.warning(
                "Skipping submodule paths in diff overlay: %s",
                ", ".join(ignored),
            )
            warnings.append(
                "submodules_ignored: " + ", ".join(ignored)
            )
            added.difference_update(ignored)
            modified.difference_update(ignored)
            deleted.difference_update(ignored)
    changed_paths = sorted(added | modified)
    deleted_paths = sorted(deleted)
    return _ChangeSet(
        changed_paths=changed_paths, deleted_paths=deleted_paths, warnings=warnings
    )


def ingest_status(
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


def build_file_records(
    repo_root: Path,
    paths: list[str],
    *,
    exclude_globs: list[str],
    ignored_paths: set[str],
) -> list[FileRecord]:
    enabled = resolve_enabled_languages(repo_root)
    exclude_spec = path_excludes.build_exclude_spec(exclude_globs)
    records: list[FileRecord] = []
    for path_str in paths:
        rel_path = Path(path_str)
        if path_excludes.is_excluded_path(
            rel_path,
            exclude_spec=exclude_spec,
            ignored_paths=ignored_paths,
        ):
            continue
        extension = rel_path.suffix.lower()
        if not extension:
            continue
        language = registry.language_for_extension(extension, enabled)
        if not language:
            continue
        abs_path = repo_root / rel_path
        if not abs_path.is_file():
            continue
        records.append(
            FileRecord(path=abs_path, relative_path=rel_path, language=language)
        )
    return records


def filter_excluded_paths(
    paths: list[str],
    *,
    repo_root: Path,
    exclude_globs: list[str],
    ignored_paths: set[str],
) -> list[str]:
    exclude_spec = path_excludes.build_exclude_spec(exclude_globs)
    filtered: list[str] = []
    for path_str in paths:
        rel_path = Path(path_str)
        if path_excludes.is_excluded_path(
            rel_path,
            exclude_spec=exclude_spec,
            ignored_paths=ignored_paths,
        ):
            continue
        filtered.append(path_str)
    return filtered


def analyze_files(
    repo_root: Path,
    records: list[FileRecord],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    if not records:
        return [], [], []
    file_snapshots = snapshot_tools.prepare_file_snapshots(repo_root, records)
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []
    calls: list[dict[str, object]] = []
    analyzers = analyzers_by_language()
    for file_snapshot in file_snapshots:
        analyzer = registry.get_analyzer_for_path(file_snapshot.record.path, analyzers)
        if not analyzer:
            continue
        module_name = analyzer.module_name(repo_root, file_snapshot)
        analysis = analyzer.analyze(file_snapshot, module_name)
        for node in analysis.nodes:
            nodes.append(node_payload(node, file_snapshot))
        for edge in analysis.edges:
            edges.append(edge_payload(edge))
        for record in analysis.call_records:
            calls.append(
                {
                    "qualified_name": record.qualified_name,
                    "node_type": record.node_type,
                    "language": file_snapshot.record.language,
                    "callee_identifiers": list(record.callee_identifiers),
                }
            )
    return nodes, edges, calls


def node_payload(node: SemanticNodeRecord, file_snapshot: FileSnapshot) -> dict[str, object]:
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
        "content_hash": node_content_hash(node, file_snapshot),
    }


def node_content_hash(node: SemanticNodeRecord, file_snapshot: FileSnapshot) -> str:
    content = file_snapshot.content
    if (
        node.start_byte is not None
        and node.end_byte is not None
        and 0 <= node.start_byte <= node.end_byte
        and node.end_byte <= len(content)
    ):
        segment = content[node.start_byte : node.end_byte]
        if segment:
            canonical = canonical_span_bytes(segment)
            if canonical:
                return hashlib.sha1(canonical).hexdigest()
    return file_snapshot.blob_sha


def edge_payload(edge) -> dict[str, object]:
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


def edge_key(src_id: str, dst_id: str, edge_type: str) -> str:
    return hashlib.sha1(f"{src_id}:{dst_id}:{edge_type}".encode("utf-8")).hexdigest()


def overlay_row(
    snapshot_id: str,
    structural_id: str,
    node_type: str,
    *,
    diff_kind: str,
    created_at: str,
    worktree_hash: str,
    field: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
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


def resolve_enabled_languages(repo_root: Path) -> list[str]:
    try:
        settings = runtime_config.load_language_settings(repo_root)
        enabled = [name for name, config in settings.items() if config.enabled]
        if enabled:
            return enabled
        return sorted(analysis_config.LANGUAGE_CONFIG.keys())
    except ConfigError:
        return sorted(analysis_config.LANGUAGE_CONFIG.keys())


def discovery_excludes(repo_root: Path) -> list[str]:
    try:
        return list(runtime_config.load_discovery_settings(repo_root).exclude_globs)
    except ConfigError:
        return []


def analyzers_by_language() -> dict[str, object]:
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
    warnings: list[str]


__all__ = [
    "analyze_files",
    "analyzers_by_language",
    "build_file_records",
    "build_node_lookup",
    "collect_changes",
    "compute_overlay_rows",
    "discovery_excludes",
    "edge_key",
    "edge_payload",
    "resolve_enabled_languages",
    "ingest_status",
    "node_content_hash",
    "node_payload",
    "overlay_row",
    "worktree_fingerprint",
]
