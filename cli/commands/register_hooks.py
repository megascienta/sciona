# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI commands for git hooks."""

from __future__ import annotations

from typing import Optional

import typer

from ...api import repo as api_repo
from ...api import runtime as api_runtime
from ..utils import cli_call
from .. import render as cli_render


def register_hooks(app: typer.Typer) -> None:
    hooks_app = typer.Typer(help="Manage SCIONA git hooks.")

    @hooks_app.command("install")
    def install(
        command: Optional[str] = typer.Option(
            None,
            "--command",
            help="Command to run in post-commit hook (default: sciona build).",
        ),
    ) -> None:
        """Install a post-commit hook to run SCIONA build."""
        repo_root = cli_call(api_runtime.get_repo_root)
        cmd = command or "sciona build"
        status = cli_call(api_repo.install_commit_hook, cmd, repo_root)
        cli_render.emit(
            [
                "Installed post-commit hook.",
                f"Path: {status.hook_path}",
                f"Command: {status.command}",
            ]
        )

    @hooks_app.command("remove")
    def remove() -> None:
        """Remove the SCIONA post-commit hook."""
        repo_root = cli_call(api_runtime.get_repo_root)
        status = cli_call(api_repo.remove_commit_hook, repo_root)
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

    @hooks_app.command("status")
    def status() -> None:
        """Show post-commit hook status."""
        repo_root = cli_call(api_runtime.get_repo_root)
        status = cli_call(api_repo.commit_hook_status, repo_root)
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

    app.add_typer(hooks_app, name="hooks")


__all__ = ["register_hooks"]
