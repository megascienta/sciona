# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI commands for repository builds."""

from __future__ import annotations

from time import perf_counter

import typer

from .. import repo_ops
from ..support.utils import cli_call
from ..support import render as cli_render


def _build_command(
    force_rebuild: bool = typer.Option(
        False,
        "--force",
        help="Bypass committed-build-input reuse and run a full rebuild.",
    ),
) -> None:
    """Create a new snapshot and ingest enabled languages (clean worktree required)."""
    started_at = perf_counter()
    result = cli_call(lambda: repo_ops.build(force_rebuild=force_rebuild))
    summary = cli_call(repo_ops.snapshot_report, snapshot_id=result.snapshot_id)
    command_wall_seconds = perf_counter() - started_at
    cli_call(
        repo_ops.record_build_wall_time,
        snapshot_id=result.snapshot_id,
        wall_seconds=command_wall_seconds,
    )
    payload = dict(result.__dict__)
    payload["summary"] = summary
    payload["command_wall_seconds"] = max(command_wall_seconds, 0.0)
    cli_render.emit(cli_render.render_build(payload))
    _emit_build_warnings(result)
    _exit_if_no_discovery(result)
    if result.status == "reused":
        typer.echo(
            f"Committed build inputs unchanged; snapshot {result.snapshot_id} reused."
        )
        return
    typer.echo(f"Snapshot {result.snapshot_id} recorded.")


def register_build(app: typer.Typer) -> None:
    app.command(name="build")(_build_command)


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
    if str(getattr(result, "health", "ok")) == "degraded":
        typer.secho(
            "Warning: build completed with degraded analysis; partial results were committed.",
            fg=typer.colors.YELLOW,
        )
    for message in list(getattr(result, "analysis_warnings", [])):
        typer.secho(f"Warning: {message}", fg=typer.colors.YELLOW)
    for message in list(getattr(result, "artifact_warnings", [])):
        typer.secho(f"Warning: {message}", fg=typer.colors.YELLOW)

__all__ = ["register_build"]
