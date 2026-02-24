# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import List

from sciona.data_storage.core_db.read_ops_snapshots import latest_committed_snapshot_id
from sciona.reducers.registry import get_reducers


def strip_json_fence(text: str) -> str:
    trimmed = text.strip()
    if trimmed.startswith("```json") and trimmed.endswith("```"):
        lines = trimmed.splitlines()
        return "\n".join(lines[1:-1])
    if trimmed.startswith("```") and trimmed.endswith("```"):
        lines = trimmed.splitlines()
        return "\n".join(lines[1:-1])
    return trimmed


def render_reducer_json(
    reducer_module,
    snapshot_id: str,
    conn,
    repo_root: Path,
    **kwargs,
) -> dict:
    payload_text = reducer_module.render(snapshot_id, conn, repo_root, **kwargs)
    return json.loads(strip_json_fence(payload_text))


def get_snapshot_id(conn: sqlite3.Connection) -> str:
    snapshot_id = latest_committed_snapshot_id(conn)
    if not snapshot_id:
        raise RuntimeError("No committed snapshot found.")
    return snapshot_id


def get_call_edges(
    snapshot_id: str,
    conn: sqlite3.Connection,
    repo_root: Path,
    *,
    function_id: str | None = None,
    method_id: str | None = None,
    callable_id: str | None = None,
) -> List[dict]:
    reducers = get_reducers()
    module = reducers["callsite_index"].module
    payload = render_reducer_json(
        module,
        snapshot_id,
        conn,
        repo_root,
        function_id=function_id,
        method_id=method_id,
        callable_id=callable_id,
        detail_level="callsites",
        direction="out",
    )
    return payload.get("edges", []) or []


def get_dependency_edges(
    snapshot_id: str,
    conn: sqlite3.Connection,
    repo_root: Path,
    module_id: str,
) -> List[dict]:
    reducers = get_reducers()
    module = reducers["dependency_edges"].module
    payload = render_reducer_json(
        module,
        snapshot_id,
        conn,
        repo_root,
        module_id=module_id,
    )
    return payload.get("edges", []) or []


def get_class_methods(
    snapshot_id: str,
    conn: sqlite3.Connection,
    repo_root: Path,
    class_id: str,
) -> List[dict]:
    reducers = get_reducers()
    module = reducers["class_overview"].module
    payload = render_reducer_json(module, snapshot_id, conn, repo_root, class_id=class_id)
    return payload.get("methods", []) or []


def get_structural_index_hash(snapshot_id: str, conn: sqlite3.Connection, repo_root: Path) -> str:
    reducers = get_reducers()
    module = reducers["structural_index"].module
    payload = module.run(snapshot_id, conn=conn, repo_root=repo_root)
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_structural_index_payload(snapshot_id: str, conn: sqlite3.Connection, repo_root: Path) -> dict:
    reducers = get_reducers()
    module = reducers["structural_index"].module
    return module.run(snapshot_id, conn=conn, repo_root=repo_root)


def get_dependency_edges_payload(
    snapshot_id: str,
    conn: sqlite3.Connection,
    repo_root: Path,
    module_id: str,
) -> dict:
    reducers = get_reducers()
    module = reducers["dependency_edges"].module
    return render_reducer_json(
        module,
        snapshot_id,
        conn,
        repo_root,
        module_id=module_id,
        direction="out",
    )


def get_callsite_index_payload(
    snapshot_id: str,
    conn: sqlite3.Connection,
    repo_root: Path,
    *,
    function_id: str | None = None,
    method_id: str | None = None,
    callable_id: str | None = None,
) -> dict:
    reducers = get_reducers()
    module = reducers["callsite_index"].module
    return render_reducer_json(
        module,
        snapshot_id,
        conn,
        repo_root,
        function_id=function_id,
        method_id=method_id,
        callable_id=callable_id,
        detail_level="callsites",
        direction="out",
    )


def get_callable_overview(
    snapshot_id: str,
    conn: sqlite3.Connection,
    repo_root: Path,
    *,
    function_id: str | None = None,
    method_id: str | None = None,
    callable_id: str | None = None,
) -> dict:
    reducers = get_reducers()
    module = reducers["callable_overview"].module
    return render_reducer_json(
        module,
        snapshot_id,
        conn,
        repo_root,
        function_id=function_id,
        method_id=method_id,
        callable_id=callable_id,
    )


def get_class_overview(
    snapshot_id: str,
    conn: sqlite3.Connection,
    repo_root: Path,
    class_id: str,
) -> dict:
    reducers = get_reducers()
    module = reducers["class_overview"].module
    return render_reducer_json(module, snapshot_id, conn, repo_root, class_id=class_id)


def get_module_overview_payload(
    snapshot_id: str,
    conn: sqlite3.Connection,
    repo_root: Path,
    module_id: str,
) -> dict:
    reducers = get_reducers()
    module = reducers["module_overview"].module
    return render_reducer_json(module, snapshot_id, conn, repo_root, module_id=module_id)


def get_module_overview(
    snapshot_id: str,
    conn: sqlite3.Connection,
    repo_root: Path,
    module_id: str,
) -> dict:
    reducers = get_reducers()
    module = reducers["module_overview"].module
    return render_reducer_json(module, snapshot_id, conn, repo_root, module_id=module_id)
