# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Prompt reducer registry (reflective metadata)."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import importlib
import pkgutil
from pathlib import Path
from types import MappingProxyType, ModuleType
from typing import Iterable, Iterator, Mapping

from .metadata import ReducerMeta

_VALID_SCOPES = {"function", "class", "module", "codebase"}
_VALID_DETERMINISM = {"strict", "conditional"}
_VALID_TAGS = {"summary", "evidence", "context", "dependency"}

_FROZEN = False


@dataclass(frozen=True)
class ReducerEntry:
    reducer_id: str
    scope: str
    placeholders: tuple[str, ...]
    determinism: str
    payload_size_stats: Mapping[str, object] | None
    semantic_tag: str
    summary: str
    lossy: bool
    baseline_only: bool
    composite: bool
    module: ModuleType


def _iter_reducer_modules() -> Iterator[ModuleType]:
    base_dir = Path(__file__).resolve().parent
    reducer_packages = ("structural", "summaries", "composites", "baseline")
    for package in reducer_packages:
        package_path = base_dir / package
        if not package_path.exists():
            continue
        module_entries = sorted(
            (entry for entry in pkgutil.iter_modules([str(package_path)])),
            key=lambda item: item.name,
        )
        for entry in module_entries:
            if entry.ispkg:
                continue
            module = importlib.import_module(f"{__package__}.{package}.{entry.name}")
            if not hasattr(module, "REDUCER_META"):
                raise ValueError(
                    f"Reducer module '{module.__name__}' is missing REDUCER_META."
                )
            yield module


def _validate_meta(meta: ReducerMeta, module_name: str) -> None:
    if meta.scope not in _VALID_SCOPES:
        raise ValueError(f"Reducer '{module_name}' has invalid scope '{meta.scope}'.")
    if meta.determinism not in _VALID_DETERMINISM:
        raise ValueError(
            f"Reducer '{module_name}' has invalid determinism '{meta.determinism}'."
        )
    if meta.semantic_tag not in _VALID_TAGS:
        raise ValueError(
            f"Reducer '{module_name}' has invalid semantic tag '{meta.semantic_tag}'."
        )
    if not meta.placeholders or len(meta.placeholders) != 1:
        raise ValueError(
            f"Reducer '{module_name}' must declare exactly one placeholder."
        )


def _build_registry() -> dict[str, ReducerEntry]:
    entries: dict[str, ReducerEntry] = {}
    for module in _iter_reducer_modules():
        meta = getattr(module, "REDUCER_META", None)
        if not isinstance(meta, ReducerMeta):
            raise ValueError(f"Reducer '{module.__name__}' is missing valid metadata.")
        _validate_meta(meta, module.__name__)
        reducer_id = meta.reducer_id
        if reducer_id in entries:
            raise ValueError(f"Duplicate reducer id '{reducer_id}'.")
        entries[reducer_id] = ReducerEntry(
            reducer_id=reducer_id,
            scope=meta.scope,
            placeholders=meta.placeholders,
            determinism=meta.determinism,
            payload_size_stats=meta.payload_size_stats,
            semantic_tag=meta.semantic_tag,
            summary=meta.summary,
            lossy=meta.lossy,
            baseline_only=meta.baseline_only,
            composite=meta.composite,
            module=module,
        )
    return entries


_REDUCERS = _build_registry()
REDUCERS: Mapping[str, ReducerEntry] = _REDUCERS


def get_reducers() -> Mapping[str, ReducerEntry]:
    return REDUCERS


def load_reducer(reducer_id: str):
    entry = REDUCERS.get(reducer_id)
    if entry is None:
        raise ValueError(f"Unknown reducer '{reducer_id}'.")
    return entry.module


def freeze_registry() -> None:
    global REDUCERS, _FROZEN
    if _FROZEN:
        return
    REDUCERS = MappingProxyType(dict(_REDUCERS))
    _FROZEN = True


def registry_frozen() -> bool:
    return _FROZEN


@contextmanager
def mutable_registry() -> Iterator[dict[str, ReducerEntry]]:
    """Temporarily expose a mutable registry (tests/addon registration)."""
    global REDUCERS, _FROZEN
    if _FROZEN:
        mutable = dict(_REDUCERS)
        REDUCERS = mutable
        _FROZEN = False
        try:
            yield mutable
        finally:
            _REDUCERS.clear()
            _REDUCERS.update(mutable)
            freeze_registry()
    else:
        yield _REDUCERS


def register_addon_reducers(modules: Iterable[ModuleType]) -> None:
    global REDUCERS
    target_registry = _REDUCERS if _FROZEN else REDUCERS
    added = False
    for module in modules:
        meta = getattr(module, "REDUCER_META", None)
        if not isinstance(meta, ReducerMeta):
            raise ValueError(f"Reducer '{module.__name__}' is missing valid metadata.")
        _validate_meta(meta, module.__name__)
        reducer_id = meta.reducer_id
        if reducer_id in target_registry:
            existing = target_registry[reducer_id]
            if existing.module is module:
                continue
            if getattr(existing.module, "__name__", None) == module.__name__:
                continue
            existing_path = getattr(existing.module, "__file__", None)
            module_path = getattr(module, "__file__", None)
            if existing_path and module_path:
                try:
                    if Path(existing_path).resolve() == Path(module_path).resolve():
                        continue
                except OSError:
                    pass
            raise ValueError(f"Duplicate reducer id '{reducer_id}'.")
        target_registry[reducer_id] = ReducerEntry(
            reducer_id=reducer_id,
            scope=meta.scope,
            placeholders=meta.placeholders,
            determinism=meta.determinism,
            payload_size_stats=meta.payload_size_stats,
            semantic_tag=meta.semantic_tag,
            summary=meta.summary,
            lossy=meta.lossy,
            baseline_only=meta.baseline_only,
            composite=meta.composite,
            module=module,
        )
        added = True
    if added and _FROZEN:
        REDUCERS = MappingProxyType(dict(_REDUCERS))


__all__ = [
    "ReducerEntry",
    "REDUCERS",
    "freeze_registry",
    "get_reducers",
    "load_reducer",
    "mutable_registry",
    "registry_frozen",
    "register_addon_reducers",
]

freeze_registry()
