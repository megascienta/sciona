# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI helper to search symbols."""

from __future__ import annotations

import json
from typing import Optional

import typer

from .. import reducer_ops
from ..support.utils import (
    cli_call,
    emit_dirty_worktree_warning,
    get_dirty_worktree_warning,
    parse_payload,
)
from ..support import render as cli_render


def register(app: typer.Typer) -> None:
    @app.command("search")
    def search(
        query: str = typer.Argument(
            ..., help="Search query (qualified name or substring)."
        ),
        kind: Optional[str] = typer.Option(
            None,
            "--kind",
            help="Filter kind: module, type, class, function, method, callable, or any.",
        ),
        limit: int = typer.Option(10, "--limit", help="Maximum matches to return."),
        json_output: bool = typer.Option(
            False, "--json", help="Emit machine-readable JSON output."
        ),
    ) -> None:
        """Search symbols in the latest committed snapshot."""
        reducer_payload, snapshot_id, _resolved_args = cli_call(
            reducer_ops.emit,
            "symbol_lookup",
            query=query,
            kind=kind,
            limit=limit,
        )
        payload = parse_payload(reducer_payload)
        if json_output:
            warning = get_dirty_worktree_warning()
            output = payload or {"payload": reducer_payload}
            output.update(
                {
                    "query": query,
                    "kind": kind,
                    "limit": limit,
                    "snapshot_id": snapshot_id,
                }
            )
            if warning:
                output["warning"] = warning
            typer.echo(json.dumps(output))
            return
        emit_dirty_worktree_warning()
        if not payload:
            cli_render.emit([json.dumps(reducer_payload, sort_keys=True)])
            return
        matches = payload.get("matches") or []
        lines = [
            f"Search '{payload.get('query')}' ({payload.get('kind') or 'any'}) -> {len(matches)} matches"
        ]
        for match in matches:
            score = match.get("score")
            lines.append(
                "  "
                f"{match.get('structural_id')} "
                f"{match.get('qualified_name')} "
                f"(file: {match.get('file_path')}) "
                f"[score: {score}]"
            )
        cli_render.emit(lines)
