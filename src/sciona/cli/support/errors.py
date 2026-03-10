# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI error adapters."""

from __future__ import annotations

import typer

from ...api.errors import ScionaError
from . import render as cli_render


def handle_cli_error(exc: Exception) -> None:
    if isinstance(exc, ScionaError):
        message = _actionize_message(str(exc))
        if message and not message.startswith("Error:"):
            message = f"Error: {message}"
        lines = cli_render.render_error(message)
        if lines:
            cli_render.emit_error(lines)
        else:
            typer.secho(str(exc), fg=typer.colors.RED)
        if exc.hint:
            typer.secho(f"Hint: {exc.hint}", fg=typer.colors.YELLOW)
        raise typer.Exit(code=exc.exit_code)
    raise exc


def _actionize_message(message: str) -> str:
    text = (message or "").strip()
    if not text:
        return text
    lowered = text.lower()
    verbs = (
        "run ",
        "edit ",
        "remove ",
        "install ",
        "configure ",
        "commit ",
        "stash ",
        "re-run ",
        "rerun ",
        "update ",
        "enable ",
        "create ",
        "delete ",
        "set ",
    )
    if lowered.startswith(verbs):
        return text
    return f"Action: {text}"


__all__ = ["handle_cli_error"]
