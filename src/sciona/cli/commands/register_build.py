# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI commands for repository builds."""

from __future__ import annotations

from datetime import datetime, timezone
import json

import typer

from ...api import cli as api_cli
from ..utils import cli_call
from .. import render as cli_render


def register_build(app: typer.Typer) -> None:
    @app.command()
    def build() -> None:
        """Create a new snapshot and ingest enabled languages (clean worktree required)."""
        result = cli_call(api_cli.build)
        cli_render.emit(cli_render.render_build(result.__dict__))
        _emit_build_warnings(result)
        _exit_if_no_discovery(result)
        if result.status == "reused":
            typer.echo(
                f"No structural diffs detected; snapshot {result.snapshot_id} reused."
            )
        else:
            typer.echo(f"Snapshot {result.snapshot_id} recorded.")
        _record_last_build(result)


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


def _record_last_build(result) -> None:
    try:
        repo_root = api_cli.get_repo_root()
        sciona_dir = api_cli.get_sciona_dir(repo_root)
        payload = {
            "snapshot_id": result.snapshot_id,
            "status": result.status,
            "files_processed": result.files_processed,
            "nodes_recorded": result.nodes_recorded,
            "enabled_languages": list(result.enabled_languages),
            "discovery_counts": result.discovery_counts,
            "discovery_candidates": result.discovery_candidates,
            "discovery_excluded_total": result.discovery_excluded_total,
            "discovery_excluded_by_glob": result.discovery_excluded_by_glob,
            "exclude_globs": list(result.exclude_globs),
            "parse_failures": result.parse_failures,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        path = sciona_dir / ".last_build.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        return


__all__ = ["register_build"]
