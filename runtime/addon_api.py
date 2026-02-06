"""Addon-facing registry API (dependency-light)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class Registry:
    cli_apps: dict[str, object] = field(default_factory=dict)

    def register_cli(self, name: str, app: object) -> None:
        if name in self.cli_apps:
            raise ValueError(f"Addon CLI '{name}' already registered.")
        self.cli_apps[name] = app

    def register_reducers(self, modules: Iterable[object]) -> None:
        raise ValueError(
            "Addon reducers are not supported. Addons must not define reducers; reducers are core-owned."
        )


__all__ = ["Registry"]
