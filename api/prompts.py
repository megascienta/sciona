"""Prompt registry API (stable)."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator, Optional

from ..prompts.registry_state import (
    _register_addon_prompts,
    freeze_registry,
    mutable_registry,
)


def register_addon_prompts(
    entries: dict[str, dict[str, object]],
    *,
    repo_root: Optional[Path] = None,
) -> None:
    _register_addon_prompts(entries, repo_root=repo_root)


__all__ = ["freeze_registry", "mutable_registry", "register_addon_prompts"]
