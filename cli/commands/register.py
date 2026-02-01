"""Repository-focused CLI commands."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import sys

import typer

from ...pipelines import repo as pipeline_commands
from ...pipelines.config import public as config
from ...pipelines.errors import ConfigError
from ..utils import cli_call
from .. import utils as cli_utils
from .. import render as cli_render


def register(app: typer.Typer) -> None:
    @app.command()
    def init(
        no_interactive: bool = typer.Option(
            False,
            "--no-interactive",
            help="Skip the interactive setup dialog.",
        ),
        agents: bool = typer.Option(
            False,
            "--agents",
            help="Generate a managed SCIONA block in AGENTS.md (no-interactive only).",
        ),
        agents_append: bool = typer.Option(
            False,
            "--agents-append",
            help="Append/update the managed SCIONA block in AGENTS.md (no-interactive only).",
        ),
        agents_overwrite: bool = typer.Option(
            False,
            "--agents-overwrite",
            help="Overwrite AGENTS.md with the managed SCIONA block (no-interactive only).",
        ),
    ) -> None:
        """Initialize SCIONA state for the current repository."""
        try:
            sciona_dir = cli_call(pipeline_commands.init)
        except ConfigError as exc:
            typer.secho(str(exc), fg=typer.colors.YELLOW)
            raise typer.Exit(code=0) from exc
        payload = {"sciona_dir": sciona_dir}
        cli_render.emit(cli_render.render_init(payload))
        _maybe_init_dialog(sciona_dir, no_interactive=no_interactive)
        _maybe_init_agents(
            no_interactive=no_interactive,
            agents=agents,
            agents_append=agents_append,
            agents_overwrite=agents_overwrite,
        )

    @app.command()
    def build() -> None:
        """Create a new snapshot and ingest enabled languages (clean worktree required)."""
        result = cli_call(pipeline_commands.build)
        cli_render.emit(cli_render.render_build(result.__dict__))
        _exit_if_no_discovery(result)
        if result.status == "reused":
            typer.echo(f"No structural diffs detected; snapshot {result.snapshot_id} reused.")
        else:
            typer.echo(f"Snapshot {result.snapshot_id} recorded.")
        _record_last_build(result)

    @app.command()
    def rebuild() -> None:
        """Clean existing SCIONA state and rebuild from scratch (clean worktree required)."""
        sciona_dir = config.get_sciona_dir(config.get_repo_root())
        if sciona_dir.exists():
            typer.echo(f"Removing existing {sciona_dir}")
        rebuild_result = cli_call(pipeline_commands.rebuild)
        result = rebuild_result.build_result
        payload = result.__dict__ | {"sciona_dir": sciona_dir}
        cli_render.emit(cli_render.render_rebuild(payload))
        _exit_if_no_discovery(result)
        _record_last_build(result)

    @app.command()
    def status() -> None:
        """Show SCIONA status for the current repository (warns if dirty)."""
        status_result = cli_call(pipeline_commands.status)
        try:
            runtime_cfg = cli_call(config.load_runtime_config, status_result.repo_root)
        except Exception:
            return
        enabled = [name for name, settings in runtime_cfg.languages.items() if settings.enabled]
        exclude_globs = runtime_cfg.discovery.exclude_globs
        last_build = None
        try:
            repo_root = status_result.repo_root
            sciona_dir = config.get_sciona_dir(repo_root)
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
        cli_utils.emit_dirty_worktree_warning(status_result.repo_root)
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
        repo_root = cli_call(config.get_repo_root)
        sciona_dir = config.get_sciona_dir(repo_root)
        removed = cli_call(pipeline_commands.clean, repo_root)
        if not removed:
            typer.secho(".sciona directory not found; nothing to clean.", fg=typer.colors.YELLOW)
            if not agents:
                raise typer.Exit(code=0)
        typer.echo(f"Removed {sciona_dir}")
        if agents:
            removed_agents = cli_call(pipeline_commands.clean_agents, repo_root)
            if removed_agents:
                typer.echo("Removed managed SCIONA block from AGENTS.md")
            else:
                typer.secho("No managed SCIONA block found in AGENTS.md.", fg=typer.colors.YELLOW)


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


def _record_last_build(result) -> None:
    try:
        repo_root = config.get_repo_root()
        sciona_dir = config.get_sciona_dir(repo_root)
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
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        path = sciona_dir / ".last_build.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        return


def _maybe_init_dialog(sciona_dir, *, no_interactive: bool) -> None:
    if no_interactive or not sys.stdin.isatty():
        return
    defaults = cli_call(pipeline_commands.init_dialog_defaults)
    detected = list(defaults.detected_languages)
    detected_display = ", ".join(detected) if detected else "none"
    typer.echo("")
    typer.echo(f"Detected languages: {detected_display}")
    default = ", ".join(detected)
    selection = typer.prompt(
        "Which languages should SCIONA analyze? (comma-separated)",
        default=default,
        show_default=bool(default),
    )
    supported = cli_call(pipeline_commands.init_supported_languages)
    selected = _parse_language_selection(selection, detected, supported)
    if selected is None:
        typer.secho("No valid languages selected; leaving defaults unchanged.", fg=typer.colors.YELLOW)
        return
    try:
        cli_call(pipeline_commands.init_apply_languages, selected)
    except Exception:
        typer.secho("Failed to update .sciona/config.yaml.", fg=typer.colors.YELLOW)


def _parse_language_selection(
    selection: str,
    default: list[str],
    supported: list[str],
) -> list[str] | None:
    raw = selection.strip()
    if not raw and default:
        return default
    if not raw:
        return []
    supported_set = set(supported)
    items = [entry.strip() for entry in raw.split(",") if entry.strip()]
    invalid = [entry for entry in items if entry not in supported_set]
    if invalid:
        typer.secho(
            f"Unknown language(s): {', '.join(invalid)}. Supported: {', '.join(sorted(supported_set))}.",
            fg=typer.colors.RED,
        )
        return None
    return items


def _maybe_init_agents(
    *,
    no_interactive: bool,
    agents: bool,
    agents_append: bool,
    agents_overwrite: bool,
) -> None:
    if agents_append or agents_overwrite:
        agents = True
    if not no_interactive and sys.stdin.isatty():
        if agents:
            typer.secho("Ignoring --agents flags in interactive mode.", fg=typer.colors.YELLOW)
        if not typer.confirm("Generate a managed SCIONA block in AGENTS.md?", default=False):
            return
        repo_root = cli_call(config.get_repo_root)
        agents_path = repo_root / "AGENTS.md"
        mode = "append"
        if agents_path.exists():
            action = typer.prompt(
                "AGENTS.md exists. Choose action [append/overwrite/skip]",
                default="append",
            ).strip().lower()
            if action == "skip":
                return
            if action == "overwrite":
                mode = "overwrite"
            elif action != "append":
                typer.secho("Unknown choice; skipping AGENTS.md update.", fg=typer.colors.YELLOW)
                return
        path = cli_call(pipeline_commands.init_agents, repo_root, mode=mode)
        typer.echo(f"Updated {path}")
        return
    if agents:
        if agents_append and agents_overwrite:
            raise typer.BadParameter("Choose only one of --agents-append or --agents-overwrite.")
        mode = "overwrite" if agents_overwrite else "append"
        path = cli_call(pipeline_commands.init_agents, config.get_repo_root(), mode=mode)
        typer.echo(f"Updated {path}")
