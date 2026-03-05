# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Interactive init helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import yaml

from ...code_analysis.core.extract.contracts import language_registry
from ...code_analysis.tools.discovery import detect_languages_from_tracked_paths
from ...runtime import git as git_ops
from ...runtime.paths import get_config_path


@dataclass(frozen=True)
class InitDialogDefaults:
    detected_languages: Sequence[str]
    supported_languages: Sequence[str] = ()
    installed_languages: Sequence[str] = ()
    missing_languages: Sequence[str] = ()


def detect_languages(repo_root: Path) -> InitDialogDefaults:
    tracked = git_ops.tracked_paths(repo_root)
    ignored = git_ops.ignored_tracked_paths(repo_root)
    availability = language_registry.language_availability()
    detected = detect_languages_from_tracked_paths(
        tracked,
        availability["installed"],
        ignored_paths=ignored,
    )
    return InitDialogDefaults(
        detected_languages=detected,
        supported_languages=availability["supported"],
        installed_languages=availability["installed"],
        missing_languages=availability["missing"],
    )


def apply_language_selection(repo_root: Path, selected: Sequence[str]) -> None:
    cfg_path = get_config_path(repo_root)
    raw_text = cfg_path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw_text) or {}
    if not isinstance(data, dict):
        data = {}
    lang_block = data.get("languages")
    if not isinstance(lang_block, dict):
        lang_block = {}
    supported = set(language_registry.supported_languages())
    for language in supported:
        entry = lang_block.get(language)
        if not isinstance(entry, dict):
            entry = {}
        entry["enabled"] = language in selected
        lang_block[language] = entry
    data["languages"] = lang_block
    cfg_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def supported_languages() -> list[str]:
    return sorted(language_registry.language_availability()["supported"])


def installed_languages() -> list[str]:
    return sorted(language_registry.language_availability()["installed"])


def missing_languages() -> list[str]:
    return sorted(language_registry.language_availability()["missing"])


__all__ = [
    "InitDialogDefaults",
    "apply_language_selection",
    "detect_languages",
    "installed_languages",
    "missing_languages",
    "supported_languages",
]
