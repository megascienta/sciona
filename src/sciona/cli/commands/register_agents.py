# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI command for regenerating AGENTS.md."""

from __future__ import annotations

import typer

from ...api import repo as api_repo
from ...api import runtime as api_runtime
from ..utils import agents_command_map, cli_call


def register_agents(app: typer.Typer) -> None:
    @app.command()
    def agents(
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
            api_repo.init_agents,
            api_runtime.get_repo_root(),
            mode=mode,
            commands=agents_command_map(),
        )
        typer.echo(f"Updated {path}")


__all__ = ["register_agents"]
