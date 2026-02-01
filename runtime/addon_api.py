"""Addon-facing registry API (dependency-light)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable


@dataclass
class Registry:
    cli_apps: dict[str, object] = field(default_factory=dict)
    init_hooks: dict[str, Callable[[Path], None]] = field(default_factory=dict)
    app_hooks: list[Callable[[object], None]] = field(default_factory=list)
    build_hooks: list[Callable[[Path, str], None]] = field(default_factory=list)
    prompt_entries: list[dict[str, dict[str, object]]] = field(default_factory=list)
    reducer_modules: list[object] = field(default_factory=list)

    def register_cli(self, name: str, app: object) -> None:
        if name in self.cli_apps:
            raise ValueError(f"Addon CLI '{name}' already registered.")
        self.cli_apps[name] = app

    def register_init(self, name: str, init_fn: Callable[[Path], None]) -> None:
        if name in self.init_hooks:
            raise ValueError(f"Addon init '{name}' already registered.")
        self.init_hooks[name] = init_fn

    def register_app_hook(self, hook: Callable[[object], None]) -> None:
        self.app_hooks.append(hook)

    def register_build_hook(self, hook: Callable[[Path, str], None]) -> None:
        self.build_hooks.append(hook)

    def register_prompts(self, entries: dict[str, dict[str, object]]) -> None:
        if entries:
            self.prompt_entries.append(entries)

    def register_reducers(self, modules: Iterable[object]) -> None:
        raise ValueError(
            "Addon reducers are not supported. Addons must not define reducers; reducers are core-owned."
        )


__all__ = ["Registry"]
