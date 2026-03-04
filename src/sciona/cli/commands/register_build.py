# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI commands for repository builds."""

from __future__ import annotations

import typer

from ...api import cli as api_cli
from ..utils import cli_call
from .. import render as cli_render


def register_build(app: typer.Typer) -> None:
    @app.command()
    def build(
        force_rebuild: bool = typer.Option(
            False,
            "--force-rebuild",
            help="Bypass fingerprint fast-path and run a full rebuild.",
        ),
    ) -> None:
        """Create a new snapshot and ingest enabled languages (clean worktree required)."""
        result = cli_call(lambda: api_cli.build(force_rebuild=force_rebuild))
        summary = cli_call(api_cli.snapshot_report, snapshot_id=result.snapshot_id)
        payload = dict(result.__dict__)
        payload["summary"] = summary
        cli_render.emit(cli_render.render_build(payload))
        _emit_build_warnings(result)
        _exit_if_no_discovery(result)
        if result.status == "reused":
            typer.echo(
                f"No structural diffs detected; snapshot {result.snapshot_id} reused."
            )
        else:
            typer.echo(f"Snapshot {result.snapshot_id} recorded.")


def _exit_if_no_discovery(result) -> None:
    total = sum(result.discovery_counts.values()) if result.discovery_counts else 0
    if total == 0:
        typer.secho("No files discovered for enabled languages.", fg=typer.colors.RED)
        typer.echo("")
        typer.echo("Check:")
        typer.echo("  - languages are enabled in .sciona/config.yaml")
        typer.echo("  - discovery.exclude_globs is not too broad")
        typer.echo("  - repository contains supported source files")
        typer.echo("")
        raise typer.Exit(code=1)


def _emit_build_warnings(result) -> None:
    for message in list(getattr(result, "analysis_warnings", [])):
        typer.secho(f"Warning: {message}", fg=typer.colors.YELLOW)
    for message in list(getattr(result, "artifact_warnings", [])):
        typer.secho(f"Warning: {message}", fg=typer.colors.YELLOW)

__all__ = ["register_build"]
