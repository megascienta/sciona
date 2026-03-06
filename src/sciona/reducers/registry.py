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

from ..runtime.reducer_metadata import (
    VALID_CATEGORIES,
    VALID_DETERMINISM,
    VALID_INVESTIGATION_ROLES,
    VALID_INVESTIGATION_STAGES,
    VALID_RISK_TIERS,
    VALID_SCOPES,
)
from .metadata import ReducerMeta

_FROZEN = False


@dataclass(frozen=True)
class ReducerEntry:
    reducer_id: str
    category: str
    scope: str
    investigation_roles: tuple[str, ...]
    risk_tier: str
    investigation_stage: str
    placeholders: tuple[str, ...]
    determinism: str
    payload_size_stats: Mapping[str, object] | None
    summary: str
    lossy: bool
    baseline_only: bool
    module: ModuleType


def _iter_reducer_modules() -> Iterator[ModuleType]:
    base_dir = Path(__file__).resolve().parent
    reducer_packages = ("core", "grounding", "analytics", "composites")
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
    if meta.category not in VALID_CATEGORIES:
        raise ValueError(
            f"Reducer '{module_name}' has invalid category '{meta.category}'."
        )
    if meta.scope not in VALID_SCOPES:
        raise ValueError(f"Reducer '{module_name}' has invalid scope '{meta.scope}'.")
    if not meta.investigation_roles:
        raise ValueError(
            f"Reducer '{module_name}' must declare at least one investigation role."
        )
    invalid_roles = [
        role for role in meta.investigation_roles if role not in VALID_INVESTIGATION_ROLES
    ]
    if invalid_roles:
        joined = ", ".join(sorted(set(invalid_roles)))
        raise ValueError(
            f"Reducer '{module_name}' has invalid investigation role(s) '{joined}'."
        )
    if meta.risk_tier not in VALID_RISK_TIERS:
        raise ValueError(
            f"Reducer '{module_name}' has invalid risk tier '{meta.risk_tier}'."
        )
    if meta.investigation_stage not in VALID_INVESTIGATION_STAGES:
        raise ValueError(
            f"Reducer '{module_name}' has invalid investigation stage "
            f"'{meta.investigation_stage}'."
        )
    if meta.determinism not in VALID_DETERMINISM:
        raise ValueError(
            f"Reducer '{module_name}' has invalid determinism '{meta.determinism}'."
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
            category=meta.category,
            scope=meta.scope,
            investigation_roles=meta.investigation_roles,
            risk_tier=meta.risk_tier,
            investigation_stage=meta.investigation_stage,
            placeholders=meta.placeholders,
            determinism=meta.determinism,
            payload_size_stats=meta.payload_size_stats,
            summary=meta.summary,
            lossy=meta.lossy,
            baseline_only=meta.baseline_only,
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
    """Temporarily expose a mutable registry (tests only)."""
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


__all__ = [
    "ReducerEntry",
    "REDUCERS",
    "freeze_registry",
    "get_reducers",
    "load_reducer",
    "mutable_registry",
    "registry_frozen",
]

freeze_registry()
