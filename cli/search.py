"""CLI helper to search symbols."""

from __future__ import annotations

import json
from typing import Optional

import typer

from ..api import reducers as reducer_api
from .utils import (
    cli_call,
    emit_dirty_worktree_warning,
    get_dirty_worktree_warning,
    parse_payload,
)
from . import render as cli_render


def register(app: typer.Typer) -> None:
    @app.command("search")
    def search(
        query: str = typer.Argument(
            ..., help="Search query (qualified name or substring)."
        ),
        kind: Optional[str] = typer.Option(
            None,
            "--kind",
            help="Filter kind: module, class, function, method, callable, or any.",
        ),
        limit: int = typer.Option(10, "--limit", help="Maximum matches to return."),
        json_output: bool = typer.Option(
            False, "--json", help="Emit machine-readable JSON output."
        ),
    ) -> None:
        """Search symbols in the latest committed snapshot."""
        reducer_text, snapshot_id, _resolved_args = cli_call(
            reducer_api.emit,
            "symbol_lookup",
            query=query,
            kind=kind,
            limit=limit,
        )
        payload = parse_payload(reducer_text)
        if json_output:
            warning = get_dirty_worktree_warning()
            output = payload or {"payload": reducer_text}
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
            cli_render.emit([reducer_text])
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
