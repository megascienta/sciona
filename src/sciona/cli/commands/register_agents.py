# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI command for regenerating AGENTS.md."""

from __future__ import annotations

import typer

from .. import repo_ops
from ..support.utils import agents_command_map, cli_call


def _agents_command(
    mode: str = typer.Option(
        "append",
        "--mode",
        help="Update mode for AGENTS.md (append or overwrite).",
    ),
) -> None:
    """Regenerate the managed SCIONA block in AGENTS.md."""
    if mode not in {"append", "overwrite"}:
        raise typer.BadParameter("Mode must be 'append' or 'overwrite'.")
    path = cli_call(
        repo_ops.init_agents,
        repo_ops.get_repo_root(),
        mode=mode,
        commands=agents_command_map(),
    )
    typer.echo(f"Updated {path}")


def register_agents(app: typer.Typer) -> None:
    app.command(name="agents")(_agents_command)


__all__ = ["register_agents"]
