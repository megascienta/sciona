# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Callable overview reducer."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ..code_analysis.tools.profiling import (
    java_function_extras,
    javascript_function_extras,
    python_function_extras,
    typescript_function_extras,
)
from .helpers.artifact.graph_edges import artifact_db_available, load_artifact_edges
from .helpers.shared.profile_utils import fetch_node_instance
from .helpers.shared import queries
from .helpers.shared.connection import require_connection
from .helpers.shared.payload import render_json_payload
from .helpers.shared.snapshot_guard import require_latest_committed_snapshot
from .helpers.shared.source_files import line_span_hash
from .helpers.shared.types import CallableOverviewPayload
from .metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="callable_overview",
    category="symbol",
    placeholder="CALLABLE_OVERVIEW",
    summary="Structural summary of a callable, including signature, location, and metadata. " \
    "Use for quick callable inspection without retrieving full source. ",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    callable_id: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    requested_identifier = callable_id
    resolved_id = queries.resolve_callable_id(conn, snapshot_id, callable_id)
    payload = run(
        snapshot_id,
        conn=conn,
        repo_root=repo_root,
        callable_id=resolved_id,
        requested_identifier=requested_identifier,
    )
    return render_json_payload(payload)


def run(snapshot_id: str, **params) -> CallableOverviewPayload:
    conn = params.get("conn")
    if conn is None:
        raise ValueError(
            "callable_overview reducer requires an active database connection."
        )
    row = conn.execute(
        "SELECT is_committed FROM snapshots WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()
    if not row or not row["is_committed"]:
        raise ValueError("callable_overview reducer requires a committed snapshot.")
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="callable_overview reducer"
    )
    resolved_id = params.get("callable_id")
    if not resolved_id:
        raise ValueError(
            "callable_overview requires 'callable_id'."
        )
    requested_identifier = params.get("requested_identifier") or resolved_id

    repo_root = params.get("repo_root")
    repo_path = Path(repo_root) if repo_root else None

    try:
        row = fetch_node_instance(conn, snapshot_id, resolved_id)
    except ValueError:
        row = _fetch_by_qualified_name(conn, snapshot_id, resolved_id)
    if row["node_type"] != "callable":
        raise ValueError(f"Node '{resolved_id}' is not a callable.")

    module_name = queries.module_id_for_structural(
        conn, snapshot_id, row["structural_id"]
    )
    module_identity = _resolve_module_identity(conn, snapshot_id, module_name)
    artifact_available = artifact_db_available(repo_path) if repo_path else False
    params_list: List[str] = []
    if row["language"] == "python":
        params_list = python_function_extras(
            row["language"],
            repo_path,
            row["file_path"],
            row["start_line"],
            row["end_line"],
        )
    elif row["language"] == "typescript":
        params_list = typescript_function_extras(
            row["language"],
            repo_path,
            row["file_path"],
            row["start_line"],
            row["end_line"],
        )
    elif row["language"] == "javascript":
        params_list = javascript_function_extras(
            row["language"],
            repo_path,
            row["file_path"],
            row["start_line"],
            row["end_line"],
        )
    elif row["language"] == "java":
        params_list = java_function_extras(
            row["language"],
            repo_path,
            row["file_path"],
            row["start_line"],
            row["end_line"],
        )
    parent = _resolve_parent(conn, snapshot_id, row["structural_id"], repo_path)
    callable_role, role_source = _infer_callable_role(
        language=row["language"],
        qualified_name=row["qualified_name"],
        parent_type=parent.get("node_type"),
        parent_qualified_name=parent.get("qualified_name"),
    )
    signature = _build_signature(row["qualified_name"], params_list)

    line_span = [row["start_line"], row["end_line"]]
    return {
        "projection": "callable_overview",
        "projection_version": "1.0",
        "payload_kind": "summary",
        "callable_id": row["structural_id"],
        "requested_identifier": requested_identifier,
        "language": row["language"],
        "module_qualified_name": module_name,
        "identity": {
            "qualified_name": row["qualified_name"],
            "module_structural_id": module_identity.get("structural_id"),
            "module_qualified_name": module_identity.get("qualified_name") or module_name,
            "module_file_path": module_identity.get("file_path"),
        },
        "file_path": row["file_path"],
        "line_span": line_span,
        "start_byte": row["start_byte"],
        "end_byte": row["end_byte"],
        "content_hash": row["content_hash"],
        "callable_role": callable_role,
        "callable_role_source": role_source,
        "line_span_hash": line_span_hash(repo_path, row["file_path"], line_span),
        "parameters": params_list,
        "signature": signature,
        "parent_structural_id": parent.get("structural_id"),
        "parent_type": parent.get("node_type"),
        "parent_qualified_name": parent.get("qualified_name"),
        "artifact_available": artifact_available,
        "edge_source": "artifact_db" if artifact_available else "none",
    }


def _resolve_parent(
    conn,
    snapshot_id: str,
    structural_id: str,
    repo_root: Path | None,
) -> Dict[str, Optional[str]]:
    if repo_root is None:
        return {"structural_id": None, "node_type": None, "qualified_name": None}
    edges = load_artifact_edges(
        repo_root,
        edge_kinds=["LEXICALLY_CONTAINS"],
        dst_ids=[structural_id],
    )
    if not edges:
        return {"structural_id": None, "node_type": None, "qualified_name": None}
    edges.sort(key=lambda entry: (entry[2], entry[0]))
    parent_id = edges[0][0]
    row = conn.execute(
        """
        SELECT sn.node_type, ni.qualified_name
        FROM structural_nodes sn
        JOIN node_instances ni
            ON ni.structural_id = sn.structural_id
            AND ni.snapshot_id = ?
        WHERE sn.structural_id = ?
        LIMIT 1
        """,
        (snapshot_id, parent_id),
    ).fetchone()
    if not row:
        return {"structural_id": None, "node_type": None, "qualified_name": None}
    return {
        "structural_id": parent_id,
        "node_type": row["node_type"],
        "qualified_name": row["qualified_name"],
    }


def _build_signature(qualified_name: str, parameters: List[str]) -> str:
    name = qualified_name.split(".")[-1]
    param_text = ", ".join(parameters)
    return f"{name}({param_text})"


def _infer_callable_role(
    *,
    language: str,
    qualified_name: str,
    parent_type: str | None,
    parent_qualified_name: str | None,
) -> tuple[str | None, str]:
    local_name = qualified_name.split(".")[-1] if qualified_name else ""
    parent_name = parent_qualified_name.split(".")[-1] if parent_qualified_name else ""
    suffix = ""
    if parent_qualified_name and qualified_name.startswith(f"{parent_qualified_name}."):
        suffix = qualified_name[len(parent_qualified_name) + 1 :]
    if language == "python" and local_name == "__init__":
        return "constructor", "inferred_constructor"
    if language in {"typescript", "javascript", "java"} and parent_type == "classifier":
        if local_name == "constructor" or (parent_name and local_name == parent_name):
            return "constructor", "inferred_constructor"
    if parent_type == "callable":
        if local_name == "default" or "." in local_name or "." in suffix:
            return "bound", "inferred_lexical_parent"
        return "nested", "inferred_lexical_parent"
    if parent_type == "module":
        if local_name == "default" or "." in local_name or "." in suffix:
            return "bound", "inferred_lexical_parent"
        return "declared", "inferred_lexical_parent"
    if parent_type == "classifier":
        if "." in local_name or "." in suffix:
            return "bound", "inferred_lexical_parent"
        return "declared", "inferred_lexical_parent"
    return None, "unknown"


def _fetch_by_qualified_name(conn, snapshot_id: str, qualified_name: str):
    row = conn.execute(
        """
        SELECT sn.structural_id,
               sn.node_type,
               sn.language,
               ni.qualified_name,
               ni.file_path,
               ni.start_line,
               ni.end_line,
               ni.start_byte,
               ni.end_byte,
               ni.content_hash
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND ni.qualified_name = ?
          AND sn.node_type = 'callable'
        LIMIT 1
        """,
        (snapshot_id, qualified_name),
    ).fetchone()
    if not row:
        raise ValueError(f"Callable '{qualified_name}' not found in snapshot.")
    return row


def _resolve_module_identity(conn, snapshot_id: str, module_name: str) -> Dict[str, Optional[str]]:
    if not module_name:
        return {"structural_id": None, "qualified_name": None, "file_path": None}
    row = conn.execute(
        """
        SELECT sn.structural_id, ni.qualified_name, ni.file_path
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type = 'module'
          AND ni.qualified_name = ?
        LIMIT 1
        """,
        (snapshot_id, module_name),
    ).fetchone()
    if not row:
        return {"structural_id": None, "qualified_name": None, "file_path": None}
    return {
        "structural_id": row["structural_id"],
        "qualified_name": row["qualified_name"],
        "file_path": row["file_path"],
    }
