"""Addon discovery and registration helpers."""
from __future__ import annotations

import os

from importlib import metadata
from .addon_api import Registry
from .logging import get_logger, debug_enabled

_LOGGER = get_logger("runtime.addons")

def load(repo_root=None) -> Registry:
    del repo_root
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


def load_for_cli(repo_root=None) -> Registry:
    return load(repo_root)


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
