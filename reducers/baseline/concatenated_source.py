"""Concatenate source reducer."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from ..helpers import queries
from ..metadata import ReducerMeta
from ..helpers.base import require_connection
from ..helpers.render import render_json_payload
from ..helpers.utils import require_latest_committed_snapshot

REDUCER_META = ReducerMeta(
    reducer_id="concatenated_source",
    scope="codebase",
    placeholders=("CONCATENATED_SOURCE",),
    determinism="conditional",
    payload_size_stats=None,
    semantic_tag="context",
    summary="Concatenated source for codebase, module, or class scope.",
    lossy=True,
    baseline_only=True,
)

MAX_SOURCE_BYTES = 200_000


def render(
    snapshot_id: str,
    conn,
    repo_root,
    scope: str | None = None,
    module_id: str | None = None,
    class_id: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="concatenated_source reducer"
    )
    resolved_scope = _normalize_scope(scope, module_id, class_id)
    if resolved_scope == "codebase":
        file_paths = _collect_snapshot_paths(conn, snapshot_id, repo_root)
    elif resolved_scope == "module":
        root = queries.resolve_module_root(conn, snapshot_id, module_id, repo_root)
        file_paths = _collect_snapshot_paths(conn, snapshot_id, repo_root, roots=[root])
    else:
        file_paths = [_resolve_class_file(conn, snapshot_id, class_id, repo_root)]
    payload = {
        "scope": resolved_scope,
        "file_count": len(file_paths),
        "files": _render_file_dump(repo_root, file_paths),
    }
    return render_json_payload(payload)


def _normalize_scope(
    scope: str | None, module_id: str | None, class_id: str | None
) -> str:
    if scope is None:
        raise ValueError("concatenated_source_v1 requires a scope.")
    normalized = scope.strip().lower()
    if normalized not in {"codebase", "module", "class"}:
        raise ValueError(
            "concatenated_source_v1 scope must be 'codebase', 'module', or 'class'."
        )
    if normalized == "module" and not module_id:
        raise ValueError("concatenated_source_v1 scope 'module' requires module_id.")
    if normalized == "class" and not class_id:
        raise ValueError("concatenated_source_v1 scope 'class' requires class_id.")
    if normalized == "codebase" and module_id:
        raise ValueError(
            "concatenated_source_v1 scope 'codebase' must not include module_id."
        )
    if normalized == "codebase" and class_id:
        raise ValueError(
            "concatenated_source_v1 scope 'codebase' must not include class_id."
        )
    if normalized == "module" and class_id:
        raise ValueError(
            "concatenated_source_v1 scope 'module' must not include class_id."
        )
    return normalized


def _resolve_class_file(conn, snapshot_id: str, class_id: str, repo_root: Path) -> Path:
    structural_id = queries.resolve_class_id(conn, snapshot_id, class_id)
    row = conn.execute(
        """
        SELECT ni.file_path
        FROM node_instances ni
        WHERE ni.snapshot_id = ?
          AND ni.structural_id = ?
        LIMIT 1
        """,
        (snapshot_id, structural_id),
    ).fetchone()
    if not row or not row["file_path"]:
        raise ValueError(
            f"Class '{class_id}' missing file_path in snapshot '{snapshot_id}'."
        )
    return _normalize_repo_relative(repo_root, Path(row["file_path"]))


def _collect_snapshot_paths(
    conn,
    snapshot_id: str,
    repo_root: Path,
    *,
    roots: Iterable[Path] | None = None,
) -> List[Path]:
    rows = conn.execute(
        """
        SELECT DISTINCT ni.file_path
        FROM node_instances ni
        WHERE ni.snapshot_id = ?
          AND ni.file_path IS NOT NULL
        ORDER BY ni.file_path
        """,
        (snapshot_id,),
    ).fetchall()
    root_list = list(roots) if roots else []
    results: List[Path] = []
    for row in rows:
        raw_path = row["file_path"]
        if not raw_path:
            continue
        rel_path = _normalize_repo_relative(repo_root, Path(raw_path))
        if root_list and not _is_under_any_root(rel_path, root_list):
            continue
        results.append(rel_path)
    return results


def _is_under_any_root(path: Path, roots: Iterable[Path]) -> bool:
    return any(path.is_relative_to(root) for root in roots)


def _normalize_repo_relative(repo_root: Path, file_path: Path) -> Path:
    if file_path.is_absolute():
        try:
            return file_path.relative_to(repo_root)
        except ValueError as exc:
            raise ValueError(f"Path '{file_path}' is outside the repo root.") from exc
    return Path(file_path.as_posix())


def _render_file_dump(
    repo_root: Path, relative_paths: Iterable[Path]
) -> List[dict[str, object]]:
    entries: List[dict[str, object]] = []
    for rel_path in relative_paths:
        header = rel_path.as_posix()
        path = repo_root / rel_path
        try:
            file_size = path.stat().st_size
        except FileNotFoundError:
            entries.append({"path": header, "status": "missing", "content": ""})
            continue
        if file_size > MAX_SOURCE_BYTES:
            entries.append({"path": header, "status": "skipped_too_large", "content": ""})
            continue
        try:
            raw = path.read_bytes()
        except FileNotFoundError:
            entries.append({"path": header, "status": "missing", "content": ""})
            continue
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            entries.append(
                {"path": header, "status": "skipped_non_utf8", "content": ""}
            )
            continue
        entries.append({"path": header, "status": "ok", "content": content})
    return entries
