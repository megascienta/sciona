"""Addon discovery and registration helpers."""
from __future__ import annotations

import importlib
import os

from importlib import metadata
from .addon_api import Registry
from .logging import get_logger, debug_enabled
from .addon_contract import PLUGIN_API_VERSION, requirement_compatible

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
        required_api = _required_plugin_api(register)
        compatible, declared = requirement_compatible(required_api)
        if not compatible:
            if declared is None:
                declared = str(required_api)
            _LOGGER.warning(
                "Addon '%s' requires plugin API '%s' but core provides '%s'. Skipping.",
                name,
                declared,
                PLUGIN_API_VERSION,
            )
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


def _required_plugin_api(register: object) -> object:
    requirement = getattr(register, "REQUIRES_SCIONA_PLUGIN_API", None)
    module_name = getattr(register, "__module__", None)
    if not isinstance(module_name, str) or not module_name:
        return requirement
    try:
        module = importlib.import_module(module_name)
    except Exception:
        return requirement
    module_requirement = getattr(module, "REQUIRES_SCIONA_PLUGIN_API", None)
    if module_requirement is not None:
        return module_requirement
    return requirement
