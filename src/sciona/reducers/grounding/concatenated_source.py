# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

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
    category="grounding",
    scope="codebase",
    placeholders=("CONCATENATED_SOURCE",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Concatenated source code for a selected scope (codebase/module/classifier). " \
    "Use for large-context reasoning or cross-entity inspection. " \
    "Scope: configurable. Payload kind: source.",
    lossy=False,
    baseline_only=True,
)

MAX_SOURCE_BYTES = 200_000


def render(
    snapshot_id: str,
    conn,
    repo_root,
    scope: str | None = None,
    module_id: str | None = None,
    classifier_id: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="concatenated_source reducer"
    )
    resolved_scope = _normalize_scope(scope, module_id, classifier_id)
    if resolved_scope == "codebase":
        file_paths = queries.collect_file_paths(conn, snapshot_id, repo_root)
    elif resolved_scope == "module":
        root = queries.resolve_module_root(conn, snapshot_id, module_id, repo_root)
        file_paths = queries.collect_file_paths(
            conn, snapshot_id, repo_root, roots=[root]
        )
    else:
        file_paths = [
            _resolve_classifier_file(conn, snapshot_id, classifier_id, repo_root)
        ]
    file_paths = sorted(file_paths, key=lambda path: path.as_posix())
    payload = {
        "payload_kind": "source",
        "scope": resolved_scope,
        "file_count": len(file_paths),
        "files": _render_file_dump(repo_root, file_paths),
    }
    return render_json_payload(payload)


def _normalize_scope(
    scope: str | None, module_id: str | None, classifier_id: str | None
) -> str:
    if scope is None:
        raise ValueError("concatenated_source requires a scope.")
    normalized = scope.strip().lower()
    if normalized not in {"codebase", "module", "classifier"}:
        raise ValueError(
            "concatenated_source scope must be 'codebase', 'module', or 'classifier'."
        )
    if normalized == "module" and not module_id:
        raise ValueError("concatenated_source scope 'module' requires module_id.")
    if normalized == "classifier" and not classifier_id:
        raise ValueError(
            "concatenated_source scope 'classifier' requires classifier_id."
        )
    if normalized == "codebase" and module_id:
        raise ValueError(
            "concatenated_source scope 'codebase' must not include module_id."
        )
    if normalized == "codebase" and classifier_id:
        raise ValueError(
            "concatenated_source scope 'codebase' must not include classifier_id."
        )
    if normalized == "module" and classifier_id:
        raise ValueError(
            "concatenated_source scope 'module' must not include classifier_id."
        )
    return normalized


def _resolve_classifier_file(
    conn, snapshot_id: str, classifier_id: str, repo_root: Path
) -> Path:
    structural_id = queries.resolve_classifier_id(conn, snapshot_id, classifier_id)
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
            f"Classifier '{classifier_id}' missing file_path in snapshot '{snapshot_id}'."
        )
    return _normalize_repo_relative(repo_root, Path(row["file_path"]))


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
