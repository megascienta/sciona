# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI commands for repository initialization."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

from ...api import errors as api_errors
from ...api import cli as api_cli
from ..support.utils import agents_command_map, cli_call
from ..support import render as cli_render


def register_init(app: typer.Typer) -> None:
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
        agents_mode: str = typer.Option(
            "append",
            "--agents-mode",
            help="Update mode for AGENTS.md (append or overwrite; no-interactive only).",
        ),
        post_commit_hook: bool = typer.Option(
            False,
            "--post-commit-hook",
            help="Install a post-commit hook that runs sciona build.",
        ),
    ) -> None:
        """Initialize SCIONA state for the current repository."""
        try:
            sciona_dir = cli_call(api_cli.init)
        except api_errors.ConfigError as exc:
            typer.secho(str(exc), fg=typer.colors.YELLOW)
            raise typer.Exit(code=0) from exc
        payload = {
            "sciona_dir": sciona_dir,
            "iterative": bool(not no_interactive and sys.stdin.isatty()),
            "config_path": sciona_dir / "config.yaml",
        }
        cli_render.emit(cli_render.render_init(payload))
        _maybe_init_dialog(sciona_dir, no_interactive=no_interactive)
        _maybe_init_agents(
            no_interactive=no_interactive,
            agents=agents,
            agents_mode=agents_mode,
        )
        _maybe_init_hook(
            sciona_dir,
            no_interactive=no_interactive,
            install=post_commit_hook,
        )


def _maybe_init_dialog(sciona_dir, *, no_interactive: bool) -> None:
    if no_interactive or not sys.stdin.isatty():
        return
    defaults = cli_call(api_cli.init_dialog_defaults)
    detected = list(defaults.detected_languages)
    detected_display = ", ".join(detected) if detected else "none"
    typer.echo(f"Detected languages: {detected_display}")
    default = ", ".join(detected)
    selection = typer.prompt(
        "Which languages should SCIONA analyze? (comma-separated)",
        default=default,
        show_default=bool(default),
    )
    supported = cli_call(api_cli.init_supported_languages)
    selected = _parse_language_selection(selection, detected, supported)
    if selected is None:
        typer.secho(
            "No valid languages selected; leaving defaults unchanged.",
            fg=typer.colors.YELLOW,
        )
        return
    try:
        cli_call(api_cli.init_apply_languages, selected)
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
    agents_mode: str,
) -> None:
    if not no_interactive and sys.stdin.isatty():
        if agents:
            typer.secho(
                "Ignoring --agents flags in interactive mode.", fg=typer.colors.YELLOW
            )
        if not typer.confirm(
            "Generate a managed SCIONA block in AGENTS.md?", default=False
        ):
            return
        repo_root = cli_call(api_cli.get_repo_root)
        agents_path = repo_root / "AGENTS.md"
        mode = "append"
        if agents_path.exists():
            action = (
                typer.prompt(
                    "AGENTS.md exists. Choose action [append/overwrite/skip]",
                    default="append",
                )
                .strip()
                .lower()
            )
            if action == "skip":
                return
            if action == "overwrite":
                mode = "overwrite"
            elif action != "append":
                typer.secho(
                    "Unknown choice; skipping AGENTS.md update.", fg=typer.colors.YELLOW
                )
                return
        path = cli_call(
            api_cli.init_agents, repo_root, mode=mode, commands=agents_command_map()
        )
        typer.echo(f"Updated {path}")
        return
    if agents:
        mode = agents_mode.strip().lower()
        if mode not in {"append", "overwrite"}:
            raise typer.BadParameter("Mode must be 'append' or 'overwrite'.")
        path = cli_call(
            api_cli.init_agents,
            api_cli.get_repo_root(),
            mode=mode,
            commands=agents_command_map(),
        )
        typer.echo(f"Updated {path}")


def _maybe_init_hook(
    sciona_dir: Path,
    *,
    no_interactive: bool,
    install: bool,
) -> None:
    repo_root = sciona_dir.parent
    cmd = "sciona build"
    if no_interactive:
        if install:
            cli_call(api_cli.install_commit_hook, cmd, repo_root)
        return
    if not sys.stdin.isatty():
        return
    if not typer.confirm(
        "Install a post-commit hook to run sciona build?", default=False
    ):
        return
    cmd_input = typer.prompt("Hook command", default=cmd, show_default=True)
    cli_call(api_cli.install_commit_hook, cmd_input.strip() or cmd, repo_root)


__all__ = ["register_init"]
