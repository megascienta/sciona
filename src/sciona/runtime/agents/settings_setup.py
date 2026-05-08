# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Managed .claude/settings.json generation helpers."""

from __future__ import annotations

import json
from pathlib import Path

CLAUDE_DIR = ".claude"
SETTINGS_FILENAME = "settings.json"

SCIONA_PERMISSIONS: list[str] = [
    "Bash(sciona --version)",
    "Bash(sciona build)",
    "Bash(sciona build *)",
    "Bash(sciona status)",
    "Bash(sciona status *)",
    "Bash(sciona reducer *)",
    "Bash(sciona search *)",
    "Bash(sciona resolve *)",
]


def upsert_claude_settings(repo_root: Path) -> Path:
    """Inject sciona permission rules into .claude/settings.json.

    Creates the file if absent. Existing non-sciona content is preserved.
    Existing sciona entries are replaced in-place to stay idempotent.
    """
    target = _settings_path(repo_root)
    _check_not_symlink(target)
    settings = _load_settings(target)
    allow: list = settings.setdefault("permissions", {}).setdefault("allow", [])
    _remove_sciona_entries(allow)
    allow.extend(SCIONA_PERMISSIONS)
    target.parent.mkdir(parents=False, exist_ok=True)
    target.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return target


def remove_claude_settings(repo_root: Path) -> bool:
    """Remove sciona permission rules from .claude/settings.json.

    Returns True if any entries were removed. Deletes the file if it becomes
    empty after removal (no permissions, no other keys).
    """
    target = _settings_path(repo_root)
    if not target.exists():
        return False
    _check_not_symlink(target)
    settings = _load_settings(target)
    allow: list = settings.get("permissions", {}).get("allow", [])
    before = len(allow)
    _remove_sciona_entries(allow)
    if len(allow) == before:
        return False
    if not allow:
        settings.get("permissions", {}).pop("allow", None)
    if not settings.get("permissions"):
        settings.pop("permissions", None)
    if not settings:
        target.unlink()
        return True
    target.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return True


def _settings_path(repo_root: Path) -> Path:
    return Path(repo_root) / CLAUDE_DIR / SETTINGS_FILENAME


def _load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Could not read {path}: {exc}") from exc
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path} contains invalid JSON and cannot be safely updated. "
            "Fix or remove the file before running this command."
        ) from exc
    if not isinstance(raw, dict):
        raise ValueError(
            f"{path} does not contain a JSON object (got {type(raw).__name__}). "
            "Fix or remove the file before running this command."
        )
    return raw

def _remove_sciona_entries(allow: list) -> None:
    managed_permissions = set(SCIONA_PERMISSIONS)
    to_remove = [e for e in allow if isinstance(e, str) and e in managed_permissions]
    for entry in to_remove:
        allow.remove(entry)


def _check_not_symlink(path: Path) -> None:
    if path.is_symlink():
        raise ValueError(
            f"{path.name} is a symbolic link. "
            "Refusing to write through it to avoid corrupting the link target. "
            "Remove or replace the symlink before running this command."
        )


__all__ = [
    "CLAUDE_DIR",
    "SETTINGS_FILENAME",
    "SCIONA_PERMISSIONS",
    "upsert_claude_settings",
    "remove_claude_settings",
]
