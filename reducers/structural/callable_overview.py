"""Callable overview reducer."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from ..helpers.artifact_graph_edges import load_artifact_edges
from ..helpers.profile_utils import (
    extract_confidence,
    fetch_node_instance,
    python_function_extras,
    typescript_function_extras,
)
from ..helpers import queries
from ..helpers.render import render_json_payload, require_connection
from ..helpers.types import FunctionOverviewPayload
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="callable_overview",
    scope="function",
    placeholders=("CALLABLE_OVERVIEW",),
    determinism="strict",
    payload_size_stats=None,
    semantic_tag="evidence",
    summary="Structural overview payload for a callable (function or method).",
)

def render(
    snapshot_id: str,
    conn,
    repo_root,
    callable_id: str | None = None,
    function_id: str | None = None,
    method_id: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    if callable_id and not (function_id or method_id):
        function_id = callable_id
    if method_id:
        resolved_id = queries.resolve_method_id(conn, snapshot_id, method_id)
    else:
        resolved_id = queries.resolve_function_id(conn, snapshot_id, function_id)
    payload = run(
        snapshot_id,
        conn=conn,
        repo_root=repo_root,
        function_id=resolved_id,
    )
    return render_json_payload(payload)


def run(snapshot_id: str, **params) -> FunctionOverviewPayload:
    conn = params.get("conn")
    if conn is None:
        raise ValueError("callable_overview reducer requires an active database connection.")
    row = conn.execute(
        "SELECT is_committed FROM snapshots WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()
    if not row or not row["is_committed"]:
        raise ValueError("callable_overview reducer requires a committed snapshot.")
    require_latest_committed_snapshot(conn, snapshot_id, reducer_name="callable_overview reducer")
    requested_id = params.get("function_id")
    if not requested_id:
        raise ValueError("callable_overview requires 'function_id' (function or method).")

    repo_root = params.get("repo_root")
    repo_path = Path(repo_root) if repo_root else None

    try:
        row = fetch_node_instance(conn, snapshot_id, requested_id)
    except ValueError:
        row = _fetch_by_qualified_name(conn, snapshot_id, requested_id)
    if row["node_type"] not in {"function", "method"}:
        raise ValueError(f"Node '{requested_id}' is not a function or method.")

    module_id = queries.module_id_for_structural(conn, snapshot_id, row["structural_id"])
    params_list: List[str] = []
    decorators: List[str] = []
    has_docstring = False
    docstring_span: Optional[List[int]] = None
    if row["language"] == "python":
        params_list, has_docstring, doc_span, decorators = python_function_extras(
            row["language"],
            repo_path,
            row["file_path"],
            row["start_line"],
            row["end_line"],
        )
        if doc_span:
            docstring_span = [doc_span[0], doc_span[1]]
    elif row["language"] == "typescript":
        params_list, decorators = typescript_function_extras(
            row["language"],
            repo_path,
            row["file_path"],
            row["start_line"],
            row["end_line"],
        )
    parent = _resolve_parent(conn, snapshot_id, row["structural_id"], repo_path)
    signature = _build_signature(row["qualified_name"], params_list)

    return {
        "projection": "callable_overview",
        "projection_version": "1.0",
        "function_id": row["structural_id"],
        "callable_id": row["structural_id"],
        "requested_identifier": requested_id,
        "language": row["language"],
        "module_id": module_id,
        "file_path": row["file_path"],
        "line_span": [row["start_line"], row["end_line"]],
        "content_hash": row["content_hash"],
        "parameters": params_list,
        "signature": signature,
        "has_docstring": has_docstring,
        "docstring_span": docstring_span,
        "decorators": decorators,
        "parent_structural_id": parent.get("structural_id"),
        "parent_type": parent.get("node_type"),
        "parent_qualified_name": parent.get("qualified_name"),
        "confidence": extract_confidence(row, repo_path),
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
        snapshot_id=snapshot_id,
        edge_kinds=["CONTAINS", "DEFINES_METHOD"],
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
               ni.content_hash
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND ni.qualified_name = ?
          AND sn.node_type IN ('function', 'method')
        LIMIT 1
        """,
        (snapshot_id, qualified_name),
    ).fetchone()
    if not row:
        raise ValueError(f"Callable '{qualified_name}' not found in snapshot.")
    return row
