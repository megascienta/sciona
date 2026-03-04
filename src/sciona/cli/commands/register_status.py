# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI commands for repository status and cleanup."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from ...api import cli as api_cli
from ..utils import (
    cli_call,
    emit_dirty_worktree_warning,
    get_dirty_worktree_warning,
)
from .. import render as cli_render


def register_status(app: typer.Typer) -> None:
    @app.command()
    def status(
        full: bool = typer.Option(
            False,
            "--full",
            help="Show per-language diagnostic details.",
        ),
        verbose: bool = typer.Option(
            False,
            "--verbose",
            help="Alias for --full.",
        ),
        json_output: bool = typer.Option(
            False,
            "--json",
            help="Emit machine-readable JSON output.",
        ),
        output: Optional[Path] = typer.Option(
            None,
            "--output",
            "-o",
            help="Write full machine-readable status payload to a JSON file.",
        ),
    ) -> None:
        """Show SCIONA status for the current repository (warns if dirty)."""
        status_result = cli_call(api_cli.status)
        detailed = bool(full or verbose)
        summary = None
        if status_result.latest_snapshot:
            summary = cli_call(
                api_cli.snapshot_report,
                snapshot_id=status_result.latest_snapshot,
                include_failure_reasons=detailed,
            )
        payload = {
            "repo_root": str(status_result.repo_root),
            "tool_version": status_result.tool_version,
            "schema_version": status_result.schema_version,
            "snapshot_count": status_result.snapshot_count,
            "latest_snapshot": status_result.latest_snapshot,
            "latest_created": status_result.latest_created,
            "db_exists": status_result.db_exists,
            "summary": summary,
            "detailed": detailed,
            "status_report_version": 1,
        }
        if json_output or output is not None:
            warning = get_dirty_worktree_warning(status_result.repo_root)
            if warning:
                payload["warning"] = warning
            text = json.dumps(payload)
            if output is not None:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(text + "\n", encoding="utf-8")
            if json_output:
                typer.echo(text)
            return
        emit_dirty_worktree_warning(status_result.repo_root)
        cli_render.emit(cli_render.render_status(payload))

    @app.command()
    def clean(
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
        repo_root = cli_call(api_cli.get_repo_root)
        sciona_dir = api_cli.get_sciona_dir(repo_root)
        removed = cli_call(api_cli.clean, repo_root)
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
            hook_before = cli_call(api_cli.commit_hook_status, repo_root)
            cli_call(api_cli.remove_commit_hook, repo_root)
            if hook_before.installed:
                typer.echo(f"Removed managed SCIONA post-commit hook block from {hook_before.hook_path}")
                cleaned_any = True
            else:
                typer.secho(
                    "No managed SCIONA post-commit hook block found.",
                    fg=typer.colors.YELLOW,
                )

        if agents:
            removed_agents = cli_call(api_cli.clean_agents, repo_root)
            if removed_agents:
                typer.echo("Removed SCIONA-managed AGENTS.md content")
                cleaned_any = True
            else:
                typer.secho(
                    "No managed SCIONA block found in AGENTS.md.",
                    fg=typer.colors.YELLOW,
                )

        if not cleaned_any:
            typer.secho("No SCIONA-managed artifacts found to clean.", fg=typer.colors.YELLOW)


__all__ = ["register_status"]
