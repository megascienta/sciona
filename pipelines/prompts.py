# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Prompt initialization helpers (pipeline-owned)."""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Dict

import yaml

_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "prompts" / "templates"
_REGISTRY_FILENAME = "registry.yaml"


def _normalize_registry(raw: object, path: Path) -> Dict[str, dict]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        if "prompts" in raw and isinstance(raw["prompts"], dict):
            raw = raw["prompts"]
        entries: Dict[str, dict] = {}
        for name, entry in raw.items():
            if not isinstance(name, str) or not name:
                raise ValueError(f"Invalid prompt name in {path}.")
            if not isinstance(entry, dict):
                raise ValueError(f"Prompt '{name}' in {path} must be a mapping.")
            entries[name] = dict(entry)
        return entries
    if isinstance(raw, list):
        entries = {}
        for entry in raw:
            if not isinstance(entry, dict):
                raise ValueError(f"Prompt entry in {path} must be a mapping.")
            name = entry.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError(f"Prompt entry in {path} missing 'name'.")
            if name in entries:
                raise ValueError(f"Duplicate prompt name '{name}' in {path}.")
            normalized = dict(entry)
            normalized.pop("name", None)
            entries[name] = normalized
        return entries
    raise ValueError(f"Invalid prompt registry format in {path}.")


def _load_registry(path: Path) -> Dict[str, dict]:
    if not path.exists():
        return {}
    raw_text = path.read_text(encoding="utf-8")
    if len(raw_text.encode("utf-8")) > 1_000_000:
        raise ValueError(f"Prompt registry {path} is too large.")
    raw = yaml.safe_load(raw_text) or {}
    return _normalize_registry(raw, path)


def _write_registry(path: Path, entries: Dict[str, dict]) -> None:
    payload = dict(entries)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def ensure_prompts_initialized(repo_root: Path) -> Path:
    from ..runtime import paths as runtime_paths

    prompts_dir = runtime_paths.get_prompts_dir(repo_root)
    prompts_dir.mkdir(parents=True, exist_ok=True)
    registry_path = runtime_paths.get_prompts_registry_path(repo_root)

    seed_registry = _load_registry(_TEMPLATES_DIR / _REGISTRY_FILENAME)
    existing_registry = _load_registry(registry_path)

    if not registry_path.exists():
        _write_registry(registry_path, seed_registry)
    else:
        # Keep user/addon entries, but always refresh core prompt entries from bundled seed.
        merged = dict(existing_registry)
        changed = False
        for name, seed_entry in seed_registry.items():
            existing_entry = existing_registry.get(name)
            if existing_entry != seed_entry:
                merged[name] = seed_entry
                changed = True
        if changed:
            _write_registry(registry_path, merged)

    for template_path in _TEMPLATES_DIR.iterdir():
        if template_path.name == _REGISTRY_FILENAME:
            continue
        target = prompts_dir / template_path.name
        # Keep bundled core specs synchronized to avoid stale placeholder/reducer mismatches.
        shutil.copy2(template_path, target)

    return prompts_dir


def custom_prompt_names(repo_root: Path) -> list[str]:
    from ..runtime import paths as runtime_paths

    registry_path = runtime_paths.get_prompts_registry_path(repo_root)
    if not registry_path.exists():
        return []
    seed_registry = _load_registry(_TEMPLATES_DIR / _REGISTRY_FILENAME)
    existing_registry = _load_registry(registry_path)
    extras = [name for name in existing_registry if name not in seed_registry]
    return sorted(extras)


__all__ = ["custom_prompt_names", "ensure_prompts_initialized"]
