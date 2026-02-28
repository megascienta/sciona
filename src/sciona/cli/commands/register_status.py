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
