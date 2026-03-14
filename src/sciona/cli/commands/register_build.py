# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI commands for repository builds."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

import typer

from .. import repo_ops
from ..support.utils import cli_call
from ..support import render as cli_render
from ...code_analysis.diagnostics.pre_persist import report as diagnostic_report


def _build_command(
    force_rebuild: bool = typer.Option(
        False,
        "--force",
        help="Bypass committed-build-input reuse and run a full rebuild.",
    ),
    diagnostic: bool = typer.Option(
        False,
        "--diagnostic",
        help="Generate repo-root diagnostic report artifacts after the build.",
    ),
    diagnostic_verbose: bool = typer.Option(
        False,
        "--verbose",
        help="With --diagnostic, also write a verbose pre-persist diagnostic sidecar.",
    ),
) -> None:
    """Create a new snapshot and ingest enabled languages (clean worktree required)."""
    started_at = perf_counter()
    result = cli_call(
        lambda: repo_ops.build(
            force_rebuild=force_rebuild,
            diagnostic=diagnostic,
            diagnostic_verbose=diagnostic_verbose,
        )
    )
    report = cli_call(repo_ops.snapshot_report, snapshot_id=result.snapshot_id)
    command_wall_seconds = perf_counter() - started_at
    cli_call(
        repo_ops.record_build_wall_time,
        snapshot_id=result.snapshot_id,
        wall_seconds=command_wall_seconds,
    )
    payload = dict(result.__dict__)
    payload["artifact_db_available"] = bool((report or {}).get("artifact_db_available"))
    payload["report"] = report
    payload["command_wall_seconds"] = max(command_wall_seconds, 0.0)
    if diagnostic and report is not None:
        _write_diagnostic_outputs(
            report=report,
            diagnostic_verbose=diagnostic_verbose,
        )
    cli_render.emit(cli_render.render_build(payload))
    _emit_build_warnings(result)
    _exit_if_no_discovery(result)
    if result.status == "reused":
        typer.echo("Committed build inputs unchanged.")
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


def _write_diagnostic_outputs(
    *,
    report: dict[str, object],
    diagnostic_verbose: bool,
) -> None:
    repo_root = Path(repo_ops.get_repo_root())
    build_status_path = diagnostic_report.build_status_output_path(repo_root)
    build_status_payload = {
        "diagnostic_mode": True,
        "diagnostic_kind": "pre_persist_filter_best_effort",
        "report": report,
    }
    build_status_path.write_text(
        json.dumps(build_status_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not diagnostic_verbose:
        return
    verbose_path = diagnostic_report.pre_persist_verbose_output_path(repo_root)
    verbose_payload = {
        "diagnostic_mode": True,
        "diagnostic_kind": "pre_persist_filter_best_effort",
        "buckets": {},
        "callsites": [],
        "files": [],
    }
    verbose_path.write_text(
        json.dumps(verbose_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

__all__ = ["register_build"]
