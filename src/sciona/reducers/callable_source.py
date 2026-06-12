# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Callable source reducer."""

from __future__ import annotations

from typing import Iterable, List

from .helpers.shared.base import (
    load_callable_overview,
    require_connection,
)
from .helpers.shared.payload import render_json_payload
from .helpers.shared.snapshot_guard import require_latest_committed_snapshot
from .helpers.shared.source_files import resolve_repo_file
from .metadata import ReducerArg, ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="callable_source",
    category="source",
    placeholder="CALLABLE_SOURCE",
    summary="Returns the full source of one callable. Use when implementation "
    "details are needed.",
    args=(
        ReducerArg(
            name="callable_id",
            type="str",
            description="Callable whose source to return; accepts qualified name or structural id.",
            required=True,
        ),
    ),
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
        raise ValueError("callable_source requires --callable-id.")
    payload = load_callable_overview(
        snapshot_id, conn, repo_root, callable_id, reducer_name="callable_source"
    )
    file_path = payload.get("file_path")
    line_span = payload.get("line_span")
    if not file_path or not line_span:
        return _format_payload(None, None, [], None)
    decorated_start_line = payload.get("decorated_start_line")
    rendered_span = _widen_line_span(line_span, decorated_start_line)
    snippet_lines = _extract_snippet(repo_root, file_path, rendered_span)
    return _format_payload(file_path, rendered_span, snippet_lines, decorated_start_line)


def _widen_line_span(
    line_span: Iterable[int], decorated_start_line: int | None
) -> List[int]:
    start_line, end_line = list(line_span)
    if decorated_start_line is not None and decorated_start_line < start_line:
        start_line = decorated_start_line
    return [start_line, end_line]


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
    decorated_start_line: int | None,
) -> str:
    source_text = "\n".join(snippet_lines) if snippet_lines else None
    payload = {
        "payload_kind": "source",
        "file_path": file_path,
        "line_span": list(line_span) if line_span else None,
        "decorated_start_line": decorated_start_line,
        "source": source_text,
    }
    return render_json_payload(payload)
