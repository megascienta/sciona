"""Prompt registry I/O helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import yaml

from .registry_validate import _registry_error


def _normalize_registry(raw: object, path: Path) -> Dict[str, dict]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        if "prompts" in raw and isinstance(raw["prompts"], dict):
            raw = raw["prompts"]
        entries: Dict[str, dict] = {}
        for name, entry in raw.items():
            if not isinstance(name, str) or not name:
                _registry_error(f"Invalid prompt name in {path}.")
            if not isinstance(entry, dict):
                _registry_error(f"Prompt '{name}' in {path} must be a mapping.")
            entries[name] = dict(entry)
        return entries
    if isinstance(raw, list):
        entries = {}
        for entry in raw:
            if not isinstance(entry, dict):
                _registry_error(f"Prompt entry in {path} must be a mapping.")
            name = entry.get("name")
            if not isinstance(name, str) or not name:
                _registry_error(f"Prompt entry in {path} missing 'name'.")
            if name in entries:
                _registry_error(f"Duplicate prompt name '{name}' in {path}.")
            normalized = dict(entry)
            normalized.pop("name", None)
            entries[name] = normalized
        return entries
    _registry_error(f"Invalid prompt registry format in {path}.")
    return {}


def _load_yaml_registry(path: Path, *, allow_missing: bool) -> Dict[str, dict]:
    if not path.exists():
        if allow_missing:
            return {}
        _registry_error(f"Missing prompt registry at {path}.")
    try:
        raw_text = path.read_text(encoding="utf-8")
        if len(raw_text.encode("utf-8")) > 1_000_000:
            _registry_error(f"Prompt registry {path} is too large.")
        raw = yaml.safe_load(raw_text) or {}
    except yaml.YAMLError as exc:
        _registry_error(f"Failed to parse prompt registry {path}: {exc}")
    except OSError as exc:
        _registry_error(f"Failed to read prompt registry {path}: {exc}")
    return _normalize_registry(raw, path)
