"""CLI error adapters."""

from __future__ import annotations

import typer

from ..api.errors import ScionaError
from . import render as cli_render


def handle_cli_error(exc: Exception) -> None:
    if isinstance(exc, ScionaError):
        lines = cli_render.render_error(str(exc))
        if lines:
            cli_render.emit_error(lines)
        else:
            typer.secho(str(exc), fg=typer.colors.RED)
        if exc.hint:
            typer.secho(f"Hint: {exc.hint}", fg=typer.colors.YELLOW)
        raise typer.Exit(code=exc.exit_code)
    raise exc


__all__ = ["handle_cli_error"]
