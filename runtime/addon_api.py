# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Addon-facing registry API (dependency-light)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class Registry:
    cli_apps: dict[str, object] = field(default_factory=dict)
    init_hooks: dict[str, object] = field(default_factory=dict)
    build_hooks: dict[str, object] = field(default_factory=dict)

    def register_cli(self, name: str, app: object) -> None:
        if name in self.cli_apps:
            raise ValueError(f"Addon CLI '{name}' already registered.")
        self.cli_apps[name] = app

    def register_init(self, name: str, hook: object) -> None:
        if name in self.init_hooks:
            raise ValueError(f"Addon init hook '{name}' already registered.")
        self.init_hooks[name] = hook

    def register_build_hook(self, hook: object) -> None:
        key = getattr(hook, "__name__", None) or f"hook_{len(self.build_hooks)}"
        if key in self.build_hooks:
            raise ValueError(f"Addon build hook '{key}' already registered.")
        self.build_hooks[key] = hook

    def register_reducers(self, modules: Iterable[object]) -> None:
        raise ValueError(
            "Addon reducers are not supported. Addons must not define reducers; reducers are core-owned."
        )


__all__ = ["Registry"]
