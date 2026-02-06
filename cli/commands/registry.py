"""CLI command registry helpers."""

from __future__ import annotations

import typer

from .register import register as register_repo


def register(app: typer.Typer) -> None:
    register_repo(app)


__all__ = ["register"]
