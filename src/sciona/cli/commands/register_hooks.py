# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI commands for git hooks."""

from __future__ import annotations

from typing import Optional

import typer

from .. import repo_ops
from ..support.utils import cli_call
from ..support import render as cli_render


def _install_hook_command(
    command: Optional[str] = typer.Option(
        None,
        "--command",
        help="Command to run in post-commit hook (default: sciona build).",
    ),
) -> None:
    """Install a post-commit hook to run SCIONA build."""
    repo_root = cli_call(repo_ops.get_repo_root)
    cmd = command or "sciona build"
    status = cli_call(repo_ops.install_commit_hook, cmd, repo_root)
    cli_render.emit(
        [
            "Installed post-commit hook.",
            f"Path: {status.hook_path}",
            f"Command: {status.command}",
        ]
    )


def _remove_hook_command() -> None:
    """Remove the SCIONA post-commit hook."""
    repo_root = cli_call(repo_ops.get_repo_root)
    status = cli_call(repo_ops.remove_commit_hook, repo_root)
    if status.installed:
        cli_render.emit(
            [
                "Removed SCIONA post-commit hook block.",
                f"Path: {status.hook_path}",
            ]
        )
        return
    cli_render.emit_warning(
        ["No managed SCIONA post-commit hook found; nothing to remove."]
    )


def _status_hook_command() -> None:
    """Show post-commit hook status."""
    repo_root = cli_call(repo_ops.get_repo_root)
    status = cli_call(repo_ops.commit_hook_status, repo_root)
    if status.installed:
        cli_render.emit(
            [
                "Post-commit hook: installed",
                f"Path: {status.hook_path}",
                f"Command: {status.command}",
            ]
        )
        return
    cli_render.emit(
        [
            "Post-commit hook: not installed",
            f"Path: {status.hook_path}",
        ]
    )


def register_hooks(app: typer.Typer) -> None:
    hooks_app = typer.Typer(help="Manage SCIONA git hooks.")
    hooks_app.command("install")(_install_hook_command)
    hooks_app.command("remove")(_remove_hook_command)
    hooks_app.command("status")(_status_hook_command)
    app.add_typer(hooks_app, name="hooks")


__all__ = ["register_hooks"]
