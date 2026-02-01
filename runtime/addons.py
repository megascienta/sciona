"""Addon discovery and registration helpers."""
from __future__ import annotations

import os
from pathlib import Path

from importlib import metadata
from .addon_api import Registry
from .logging import get_logger, debug_enabled

_LOGGER = get_logger("runtime.addons")

def load(repo_root: Path) -> Registry:
    registry = Registry()
    if _addons_disabled():
        return registry
    installed = _discover_installed_addons()
    enabled = _load_enabled_addon_list(list(installed.keys()))
    if not enabled:
        return registry
    for name in enabled:
        entry = installed.get(name)
        if entry is None:
            _LOGGER.warning("Addon '%s' is enabled but not installed.", name)
            continue
        try:
            register = entry.load()
        except Exception as exc:
            if debug_enabled():
                _LOGGER.exception("Addon '%s' failed to load: %s", name, exc)
            else:
                _LOGGER.warning("Addon '%s' failed to load: %s", name, exc)
            continue
        if not callable(register):
            _LOGGER.warning("Addon '%s' entry point is not callable.", name)
            continue
        try:
            register(registry)
        except Exception as exc:
            if debug_enabled():
                _LOGGER.exception("Addon '%s' failed to register: %s", name, exc)
            else:
                _LOGGER.warning("Addon '%s' failed to register: %s", name, exc)
            continue
    return registry


def load_for_cli(repo_root: Path | None = None) -> Registry:
    registry = Registry()
    if _addons_disabled():
        return registry
    installed = _discover_installed_addons()
    for name, entry in installed.items():
        try:
            register = entry.load()
        except Exception as exc:
            if debug_enabled():
                _LOGGER.exception("Addon '%s' failed to load: %s", name, exc)
            else:
                _LOGGER.warning("Addon '%s' failed to load: %s", name, exc)
            continue
        if not callable(register):
            _LOGGER.warning("Addon '%s' entry point is not callable.", name)
            continue
        try:
            register(registry)
        except Exception as exc:
            if debug_enabled():
                _LOGGER.exception("Addon '%s' failed to register: %s", name, exc)
            else:
                _LOGGER.warning("Addon '%s' failed to register: %s", name, exc)
            continue
    return registry


def apply_prompts_and_reducers(registry: Registry, *, repo_root: Path) -> None:
    if registry.reducer_modules:
        from ..reducers import registry as reducer_registry

        if reducer_registry.registry_frozen():
            with reducer_registry.mutable_registry():
                reducer_registry.register_addon_reducers(registry.reducer_modules)
        else:
            reducer_registry.register_addon_reducers(registry.reducer_modules)
    if registry.prompt_entries:
        from ..prompts import registry as prompt_registry

        for entries in registry.prompt_entries:
            if prompt_registry.registry_frozen():
                with prompt_registry.mutable_registry(repo_root=repo_root):
                    prompt_registry.register_addon_prompts(entries, repo_root=repo_root)
            else:
                prompt_registry.register_addon_prompts(entries, repo_root=repo_root)

def apply_app_hooks(registry: Registry, app: object) -> None:
    for hook in registry.app_hooks:
        try:
            hook(app)
        except Exception as exc:
            if debug_enabled():
                _LOGGER.exception("Addon app hook failed: %s", exc)
            else:
                _LOGGER.warning("Addon app hook failed: %s", exc)

def apply_build_hooks(
    registry: Registry,
    *,
    repo_root: Path,
    snapshot_id: str,
) -> None:
    for hook in registry.build_hooks:
        try:
            hook(repo_root, snapshot_id)
        except Exception as exc:
            if debug_enabled():
                _LOGGER.exception("Addon build hook failed: %s", exc)
            else:
                _LOGGER.warning("Addon build hook failed: %s", exc)


def run_inits(registry: Registry, *, repo_root: Path) -> None:
    for name, init_fn in registry.init_hooks.items():
        try:
            init_fn(repo_root)
        except Exception as exc:
            _LOGGER.warning("Addon '%s' init failed: %s", name, exc)


def run_build_hooks(*, repo_root: Path, snapshot_id: str) -> None:
    registry = load(repo_root)
    if not registry.build_hooks:
        return
    apply_build_hooks(registry, repo_root=repo_root, snapshot_id=snapshot_id)


def _load_enabled_addon_list(installed: list[str]) -> list[str]:
    return sorted(installed)


def _discover_installed_addons() -> dict[str, metadata.EntryPoint]:
    entries = metadata.entry_points()
    group = entries.select(group="sciona.addons")
    discovered: dict[str, metadata.EntryPoint] = {}
    for entry in group:
        discovered[entry.name] = entry
    return discovered


def _addons_disabled() -> bool:
    return _env_flag("SCIONA_DISABLE_ADDONS") or _env_flag("SCIONA_SAFE_MODE")


def _env_flag(name: str) -> bool:
    value = os.getenv(name)
    if not value:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def is_enabled(repo_root: Path, name: str) -> bool:
    if _addons_disabled():
        return False
    installed = _discover_installed_addons()
    return name in installed
