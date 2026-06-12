# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI helper to resolve identifiers."""

from __future__ import annotations

import json
from typing import Optional

import typer

from .. import resolve_ops
from ..support.utils import cli_call, emit_dirty_worktree_warning, get_dirty_worktree_warning
from ..support import render as cli_render


def _resolve_command(
    identifier: str = typer.Argument(..., help="Structural id or qualified name."),
    kind: Optional[str] = typer.Option(
        None,
        "--kind",
        help=(
            "Identifier kind: callable, type, class, function, method, or module. "
            "Searches all kinds when omitted."
        ),
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
        if result.resolved_from is not None:
            payload["resolved_from"] = result.resolved_from
        if warning:
            payload["warning"] = warning
        typer.echo(json.dumps(payload))
        return
    emit_dirty_worktree_warning()
    if result.status in ("exact", "resolved") and result.resolved_id:
        candidate = next(
            (
                item
                for item in result.candidates
                if item.structural_id == result.resolved_id
            ),
            None,
        )
        kind_label = kind or "identifier"
        lines = [f"Resolved {kind_label} '{identifier}' -> {result.resolved_id}"]
        if candidate:
            lines.append(
                f"  qualified_name={candidate.qualified_name} "
                f"language={candidate.language} "
                f"node_type={candidate.node_type} "
                f"file={candidate.file_path} "
                f"id={candidate.structural_id}"
            )
        if result.status == "resolved" and result.resolved_from is not None:
            score = f", score {candidate.score}" if candidate else ""
            lines.append(f"  (auto-resolved from '{result.resolved_from}'{score})")
        cli_render.emit(lines)
        return
    message = resolve_ops.format_resolution_message(kind, identifier, result)
    cli_render.emit(message.splitlines())


def register(app: typer.Typer) -> None:
    app.command("resolve")(_resolve_command)
