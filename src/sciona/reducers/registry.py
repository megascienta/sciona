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
    VALID_INVESTIGATION_STAGES,
    VALID_RISK_TIERS,
)
from .metadata import ReducerMeta

_FROZEN = False


@dataclass(frozen=True)
class ReducerEntry:
    reducer_id: str
    category: str
    placeholder: str
    risk_tier: str
    stage: str
    summary: str
    anomaly_detector: bool
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
    if meta.risk_tier not in VALID_RISK_TIERS:
        raise ValueError(
            f"Reducer '{module_name}' has invalid risk tier '{meta.risk_tier}'."
        )
    if meta.stage not in VALID_INVESTIGATION_STAGES:
        raise ValueError(
            f"Reducer '{module_name}' has invalid investigation stage "
            f"'{meta.stage}'."
        )
    if not str(meta.placeholder).strip():
        raise ValueError(
            f"Reducer '{module_name}' must declare a non-empty placeholder."
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
            placeholder=meta.placeholder,
            risk_tier=meta.risk_tier,
            stage=meta.stage,
            summary=meta.summary,
            anomaly_detector=meta.anomaly_detector,
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
