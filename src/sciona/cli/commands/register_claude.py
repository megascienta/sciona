# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI command for Claude Code setup (CLAUDE.md + .claude/settings.json)."""

from __future__ import annotations

import typer

from .. import repo_ops
from ..support.utils import agents_command_map, cli_call


def _claude_command(
    mode: str = typer.Option(
        "append",
        "--mode",
        help="Update mode for CLAUDE.md (append or overwrite).",
    ),
) -> None:
    """Set up Claude Code integration: CLAUDE.md and .claude/settings.json."""
    if mode not in {"append", "overwrite"}:
        raise typer.BadParameter("Mode must be 'append' or 'overwrite'.")
    repo_root = repo_ops.get_repo_root()
    path = cli_call(
        repo_ops.init_claude,
        repo_root,
        mode=mode,
        commands=agents_command_map(),
    )
    typer.echo(f"Updated {path}")
    settings_path = cli_call(repo_ops.init_claude_settings, repo_root)
    typer.echo(f"Updated {settings_path}")


def register_claude(app: typer.Typer) -> None:
    app.command(name="claude")(_claude_command)


__all__ = ["register_claude"]
