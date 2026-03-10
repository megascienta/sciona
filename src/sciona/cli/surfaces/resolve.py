# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI helper to resolve identifiers."""

from __future__ import annotations

import json

import typer

from .. import resolve_ops
from ..support.utils import cli_call, emit_dirty_worktree_warning, get_dirty_worktree_warning
from ..support import render as cli_render


def register(app: typer.Typer) -> None:
    @app.command("resolve")
    def resolve(
        identifier: str = typer.Argument(..., help="Structural id or qualified name."),
        kind: str = typer.Option(
            ...,
            "--kind",
            help="Identifier kind: callable, type, class, function, method, or module.",
        ),
        limit: int = typer.Option(5, "--limit", help="Maximum candidates to return."),
        json_output: bool = typer.Option(
            False, "--json", help="Emit machine-readable JSON output."
        ),
    ) -> None:
        """Resolve an identifier to a structural id (latest committed snapshot only)."""
        result = cli_call(
            resolve_ops.identifier_for_repo,
            kind=kind,
            identifier=identifier,
            limit=limit,
        )
        if json_output:
            warning = get_dirty_worktree_warning()
            payload = {
                "kind": kind,
                "identifier": identifier,
                "status": result.status,
                "resolved_id": result.resolved_id,
                "candidates": [
                    {
                        "structural_id": item.structural_id,
                        "node_type": item.node_type,
                        "language": item.language,
                        "qualified_name": item.qualified_name,
                        "file_path": item.file_path,
                        "score": item.score,
                    }
                    for item in result.candidates
                ],
            }
            if warning:
                payload["warning"] = warning
            typer.echo(json.dumps(payload))
            return
        emit_dirty_worktree_warning()
        if result.status == "exact" and result.resolved_id:
            candidate = result.candidates[0] if result.candidates else None
            lines = [f"Resolved {kind} '{identifier}' -> {result.resolved_id}"]
            if candidate:
                lines.append(
                    f"  {candidate.language}:{candidate.qualified_name} (file: {candidate.file_path})"
                )
            cli_render.emit(lines)
            return
        message = resolve_ops.format_resolution_message(kind, identifier, result)
        cli_render.emit(message.splitlines())
