# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Callable source reducer."""

from __future__ import annotations

from typing import Iterable, List

from ..helpers.base import (
    load_callable_overview,
    require_connection,
)
from ..helpers.render import render_json_payload
from ..helpers.utils import require_latest_committed_snapshot, resolve_repo_file
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="callable_source",
    category="grounding",
    scope="callable",
    investigation_roles=("source",),
    risk_tier="elevated",
    investigation_stage="source_verification",
    placeholders=("CALLABLE_SOURCE",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Full source code of a callable. Use only when " \
    "implementation details are required. Scope: single callable. Payload kind: source.",
    lossy=False,
    baseline_only=True,
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    callable_id: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="callable_source reducer"
    )
    if not callable_id:
        raise ValueError(
            "CALLABLE_SOURCE requires callable_id."
        )
    payload = load_callable_overview(snapshot_id, conn, repo_root, callable_id)
    file_path = payload.get("file_path")
    line_span = payload.get("line_span")
    if not file_path or not line_span:
        return _format_payload(None, None, [])
    snippet_lines = _extract_snippet(repo_root, file_path, line_span)
    return _format_payload(file_path, line_span, snippet_lines)


def _extract_snippet(
    repo_root, relative_path: str, line_span: Iterable[int]
) -> List[str]:
    file_path = resolve_repo_file(repo_root, relative_path)
    if file_path is None:
        return []
    try:
        text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    try:
        start_line, end_line = list(line_span)
    except ValueError:
        return []
    start_index = max(0, start_line - 1)
    end_index = min(len(lines), end_line)
    return lines[start_index:end_index]


def _format_payload(
    file_path: str | None,
    line_span: Iterable[int] | None,
    snippet_lines: List[str],
) -> str:
    source_text = "\n".join(snippet_lines) if snippet_lines else None
    payload = {
        "payload_kind": "source",
        "file_path": file_path,
        "line_span": list(line_span) if line_span else None,
        "source": source_text,
    }
    return render_json_payload(payload)
