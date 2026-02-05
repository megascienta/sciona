"""Repository-focused CLI commands (aggregator)."""
from __future__ import annotations

import typer

from .register_build import register_build
from .register_init import register_init
from .register_status import register_status


def register(app: typer.Typer) -> None:
    register_init(app)
    register_build(app)
    register_status(app)


__all__ = ["register"]
