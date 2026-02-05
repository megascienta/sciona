"""Prompt registry state and accessors."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import MappingProxyType
from typing import Iterator, Mapping, Optional

from ..runtime.errors import EnvError
from .registry_io import _load_yaml_registry
from .registry_validate import _registry_error, _validate_registry

_FROZEN = False
_LAST_REPO_ROOT: Optional[Path] = None

_PROMPTS: dict[str, dict[str, object]] = {}
_ADDON_PROMPTS: dict[str, dict[str, object]] = {}
PROMPTS: Mapping[str, Mapping[str, object]] = _PROMPTS


def _resolve_repo_root(repo_root: Optional[Path]) -> Optional[Path]:
    if repo_root is None:
        try:
            from ..runtime import paths as runtime_paths
            return runtime_paths.get_repo_root()
        except EnvError:
            return None
    return repo_root


def _load_registry(repo_root: Optional[Path]) -> dict[str, dict[str, object]]:
    repo_entries: dict[str, dict[str, object]] = {}
    if repo_root is not None:
        from ..runtime import paths as runtime_paths
        registry_path = runtime_paths.get_prompts_registry_path(repo_root)
        repo_entries = _load_yaml_registry(registry_path, allow_missing=True)
        if repo_entries:
            _validate_registry(repo_entries, repo_root=repo_root, source="repo")
    merged: dict[str, dict[str, object]] = {}
    for name, entry in repo_entries.items():
        if name in merged:
            _registry_error(f"Duplicate prompt name '{name}' in registry.")
        merged[name] = entry
    for name, entry in _ADDON_PROMPTS.items():
        if name in merged:
            _registry_error(f"Duplicate prompt name '{name}' in addon registry.")
        merged[name] = entry
    return merged


def _freeze_registry(entries: dict[str, dict[str, object]]) -> Mapping[str, Mapping[str, object]]:
    frozen: dict[str, Mapping[str, object]] = {}
    for name, entry in entries.items():
        frozen_entry: dict[str, object] = {}
        for key, value in entry.items():
            if isinstance(value, list):
                frozen_entry[key] = tuple(value)
            elif isinstance(value, dict):
                frozen_entry[key] = MappingProxyType(dict(value))
            else:
                frozen_entry[key] = value
        frozen[name] = MappingProxyType(frozen_entry)
    return MappingProxyType(frozen)


def _refresh_registry(repo_root: Optional[Path]) -> None:
    global _PROMPTS, PROMPTS, _LAST_REPO_ROOT
    if _LAST_REPO_ROOT == repo_root and _PROMPTS:
        return
    _PROMPTS = _load_registry(repo_root)
    PROMPTS = _freeze_registry(_PROMPTS) if _FROZEN else _PROMPTS
    _LAST_REPO_ROOT = repo_root


def get_prompts(repo_root: Optional[Path] = None) -> Mapping[str, Mapping[str, object]]:
    repo_root = _resolve_repo_root(repo_root)
    _refresh_registry(repo_root)
    return PROMPTS


def registry_frozen() -> bool:
    return _FROZEN


def freeze_registry(repo_root: Optional[Path] = None) -> None:
    global PROMPTS, _FROZEN
    if _FROZEN:
        return
    repo_root = _resolve_repo_root(repo_root)
    _refresh_registry(repo_root)
    PROMPTS = _freeze_registry(_PROMPTS)
    _FROZEN = True


@contextmanager
def mutable_registry(repo_root: Optional[Path] = None) -> Iterator[dict[str, dict[str, object]]]:
    """Temporarily expose a mutable registry (for tests only)."""
    global PROMPTS, _FROZEN
    repo_root = _resolve_repo_root(repo_root)
    _refresh_registry(repo_root)
    if _FROZEN:
        mutable: dict[str, dict[str, object]] = {}
        for name, entry in _PROMPTS.items():
            mutable[name] = dict(entry)
        PROMPTS = mutable
        _FROZEN = False
        try:
            yield mutable
        finally:
            _PROMPTS.clear()
            _PROMPTS.update(mutable)
            freeze_registry(repo_root)
    else:
        yield _PROMPTS


def _register_addon_prompts(
    entries: dict[str, dict[str, object]],
    *,
    repo_root: Optional[Path] = None,
) -> None:
    if _FROZEN:
        raise RuntimeError("Cannot register addon prompts after registry is frozen.")
    if not entries:
        return
    repo_root = _resolve_repo_root(repo_root)
    _validate_registry(entries, repo_root=repo_root, source="addon")
    for name, entry in entries.items():
        normalized = dict(entry)
        normalized["_source"] = "addon"
        if name in _ADDON_PROMPTS:
            existing = _ADDON_PROMPTS[name]
            if existing == normalized:
                continue
            _registry_error(f"Duplicate addon prompt name '{name}'.")
        _ADDON_PROMPTS[name] = normalized
    _refresh_registry(repo_root)
