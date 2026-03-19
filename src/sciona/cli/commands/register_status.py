# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI commands for repository status and cleanup."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import typer

from .. import repo_ops
from ..support.utils import (
    cli_call,
    emit_dirty_worktree_warning,
    get_dirty_worktree_warning,
)
from ..support import render as cli_render


def _status_command(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Show per-language diagnostic details in text output.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write full machine-readable status payload to a JSON file.",
    ),
) -> None:
    """Show SCIONA status for the current repository (warns if dirty)."""
    status_result = cli_call(repo_ops.status)
    export_mode = bool(output is not None)
    detailed = bool(verbose) if not export_mode else True
    include_failure_reasons = bool(detailed or export_mode)
    report = None
    artifact_db_available = False
    if status_result.latest_snapshot:
        report = cli_call(
            repo_ops.snapshot_report,
            snapshot_id=status_result.latest_snapshot,
            include_failure_reasons=include_failure_reasons,
        )
        artifact_db_available = bool((report or {}).get("artifact_db_available"))
    payload = {
        "repo_root": str(status_result.repo_root),
        "tool_version": status_result.tool_version,
        "schema_version": status_result.schema_version,
        "snapshot_count": status_result.snapshot_count,
        "latest_snapshot": status_result.latest_snapshot,
        "latest_created": status_result.latest_created,
        "db_exists": status_result.db_exists,
        "artifact_db_available": artifact_db_available,
        "report": report,
        "build_health": status_result.build_health,
        "parse_failures": status_result.parse_failures,
        "residual_containment_failures": status_result.residual_containment_failures,
        "detailed": detailed,
        "status_report_version": 1,
    }
    if export_mode:
        payload["repo_root"] = os.path.relpath(
            str(status_result.repo_root), start=os.getcwd()
        )
        warning = get_dirty_worktree_warning(status_result.repo_root)
        if warning:
            payload["warning"] = warning
        text = json.dumps(payload)
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text + "\n", encoding="utf-8")
    if not export_mode:
        emit_dirty_worktree_warning(status_result.repo_root)
        cli_render.emit(cli_render.render_status(payload))

def _clean_command(
    hooks: bool = typer.Option(
        True,
        "--hooks/--no-hooks",
        help="Remove the managed SCIONA post-commit hook block.",
    ),
    agents: bool = typer.Option(
        True,
        "--agents/--no-agents",
        help="Remove SCIONA-managed content from AGENTS.md.",
    ),
) -> None:
    """Remove SCIONA state and managed integrations for the current repository."""
    repo_root = cli_call(repo_ops.get_repo_root)
    sciona_dir = repo_ops.get_sciona_dir(repo_root)
    removed = cli_call(repo_ops.clean, repo_root)
    cleaned_any = False
    if removed:
        typer.echo(f"Removed {sciona_dir}")
        cleaned_any = True
    else:
        typer.secho(
            ".sciona directory not found; nothing to clean there.",
            fg=typer.colors.YELLOW,
        )

    if hooks:
        hook_before = cli_call(repo_ops.commit_hook_status, repo_root)
        cli_call(repo_ops.remove_commit_hook, repo_root)
        if hook_before.installed:
            typer.echo(
                f"Removed managed SCIONA post-commit hook block from {hook_before.hook_path}"
            )
            cleaned_any = True
        else:
            typer.secho(
                "No managed SCIONA post-commit hook block found.",
                fg=typer.colors.YELLOW,
            )

    if agents:
        removed_agents = cli_call(repo_ops.clean_agents, repo_root)
        if removed_agents:
            typer.echo("Removed SCIONA-managed AGENTS.md content")
            cleaned_any = True
        else:
            typer.secho(
                "No managed SCIONA block found in AGENTS.md.",
                fg=typer.colors.YELLOW,
            )

    if not cleaned_any:
        typer.secho(
            "No SCIONA-managed artifacts found to clean.",
            fg=typer.colors.YELLOW,
        )


def register_status(app: typer.Typer) -> None:
    app.command(name="status")(_status_command)
    app.command(name="clean")(_clean_command)


__all__ = ["register_status"]
