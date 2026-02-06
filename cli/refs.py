"""CLI helper to list module import references."""

from __future__ import annotations

import json
from typing import Optional

import typer

from ..api import reducers as reducer_api
from ..api import resolve as resolver
from .utils import (
    cli_call,
    emit_dirty_worktree_warning,
    get_dirty_worktree_warning,
    parse_payload,
)
from . import render as cli_render


def register(app: typer.Typer) -> None:
    @app.command("refs")
    def refs(
        identifier: str = typer.Argument(
            ..., help="Module identifier or qualified name."
        ),
        kind: str = typer.Option(
            "module",
            "--kind",
            help="Identifier kind (module only).",
        ),
        limit: int = typer.Option(50, "--limit", help="Maximum references to return."),
        edge_type: Optional[str] = typer.Option(
            None,
            "--edge-type",
            help="Edge type filter (default IMPORTS_DECLARED; use 'any' for all).",
        ),
        json_output: bool = typer.Option(
            False, "--json", help="Emit machine-readable JSON output."
        ),
    ) -> None:
        """List modules that import the target module (latest committed snapshot only)."""
        normalized_kind = str(kind).strip().lower()
        if normalized_kind != "module":
            raise typer.BadParameter("refs only supports --kind module.")
        result = cli_call(
            resolver.identifier_for_repo,
            kind="module",
            identifier=identifier,
            limit=5,
        )
        if result.status != "exact" or not result.resolved_id:
            emit_dirty_worktree_warning()
            message = resolver.format_resolution_message("module", identifier, result)
            cli_render.emit(message.splitlines())
            return
        reducer_text, snapshot_id, resolved_args = cli_call(
            reducer_api.emit,
            "import_references",
            module_id=result.resolved_id,
            limit=limit,
            edge_type=edge_type,
        )
        payload = parse_payload(reducer_text)
        if json_output:
            warning = get_dirty_worktree_warning()
            output = {
                "identifier": identifier,
                "kind": "module",
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
                "snapshot_id": snapshot_id,
                "args": resolved_args,
                "payload": payload or {"payload": reducer_text},
            }
            if warning:
                output["warning"] = warning
            typer.echo(json.dumps(output))
            return
        emit_dirty_worktree_warning()
        if not payload:
            cli_render.emit([reducer_text])
            return
        edges = payload.get("edges") or []
        target_name = _first_target_name(payload)
        lines = [
            f"Import refs for {target_name or result.resolved_id} -> {len(edges)} matches"
        ]
        for edge in edges:
            lines.append(
                "  "
                f"{edge.get('from_module_structural_id')} "
                f"{edge.get('from_module_qualified_name')} "
                f"(file: {edge.get('from_file_path')}) "
                f"[edge: {edge.get('edge_type')}]"
            )
        cli_render.emit(lines)


def _first_target_name(payload: dict) -> Optional[str]:
    targets = payload.get("targets") or []
    if targets:
        first = targets[0]
        name = first.get("module_qualified_name") if isinstance(first, dict) else None
        if name:
            return str(name)
    return None
