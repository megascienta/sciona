# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI commands for repository status and cleanup."""

from __future__ import annotations

import json

import typer

from ...api import cli as api_cli
from ..utils import cli_call, emit_dirty_worktree_warning
from .. import render as cli_render


def register_status(app: typer.Typer) -> None:
    @app.command()
    def status() -> None:
        """Show SCIONA status for the current repository (warns if dirty)."""
        status_result = cli_call(api_cli.status)
        enabled: list[str] | None = None
        exclude_globs: list[str] = []
        try:
            runtime_cfg = cli_call(
                api_cli.load_runtime_config, status_result.repo_root
            )
            enabled = [
                name
                for name, settings in runtime_cfg.languages.items()
                if settings.enabled
            ]
            exclude_globs = runtime_cfg.discovery.exclude_globs
        except Exception:
            cli_render.emit_warning(
                ["Failed to load runtime config; discovery settings unavailable."]
            )
        last_build = None
        try:
            repo_root = status_result.repo_root
            sciona_dir = api_cli.get_sciona_dir(repo_root)
            path = sciona_dir / ".last_build.json"
            if path.exists():
                last_build = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            last_build = None
        payload = {
            "repo_root": status_result.repo_root,
            "tool_version": status_result.tool_version,
            "schema_version": status_result.schema_version,
            "snapshot_count": status_result.snapshot_count,
            "latest_snapshot": status_result.latest_snapshot,
            "latest_created": status_result.latest_created,
            "db_exists": status_result.db_exists,
            "enabled_languages": enabled,
            "exclude_globs_count": len(exclude_globs),
            "exclude_globs": exclude_globs,
            "last_build": last_build,
        }
        emit_dirty_worktree_warning(status_result.repo_root)
        cli_render.emit(cli_render.render_status(payload))

    @app.command()
    def clean(
        agents: bool = typer.Option(
            False,
            "--agents",
            help="Remove the managed SCIONA block from AGENTS.md.",
        ),
    ) -> None:
        """Remove the SCIONA state directory for the current repository."""
        repo_root = cli_call(api_cli.get_repo_root)
        sciona_dir = api_cli.get_sciona_dir(repo_root)
        removed = cli_call(api_cli.clean, repo_root)
        if not removed:
            typer.secho(
                ".sciona directory not found; nothing to clean.", fg=typer.colors.YELLOW
            )
            if not agents:
                raise typer.Exit(code=0)
        typer.echo(f"Removed {sciona_dir}")
        if agents:
            removed_agents = cli_call(api_cli.clean_agents, repo_root)
            if removed_agents:
                typer.echo("Removed managed SCIONA block from AGENTS.md")
            else:
                typer.secho(
                    "No managed SCIONA block found in AGENTS.md.",
                    fg=typer.colors.YELLOW,
                )


__all__ = ["register_status"]
