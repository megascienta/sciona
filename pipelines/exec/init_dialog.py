"""Interactive init helpers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import yaml

from ...code_analysis import config as analysis_config
from ...code_analysis.tools import git_support
from ...runtime.paths import get_config_path


@dataclass(frozen=True)
class InitDialogDefaults:
    detected_languages: Sequence[str]


def detect_languages(repo_root: Path) -> InitDialogDefaults:
    tracked = git_support.tracked_paths(repo_root)
    detected: set[str] = set()
    for path_str in tracked:
        suffix = Path(path_str).suffix.lower()
        if not suffix:
            continue
        for language, cfg in analysis_config.LANGUAGE_CONFIG.items():
            if suffix in cfg.extensions:
                detected.add(language)
    return InitDialogDefaults(detected_languages=sorted(detected))


def apply_language_selection(repo_root: Path, selected: Sequence[str]) -> None:
    cfg_path = get_config_path(repo_root)
    raw_text = cfg_path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw_text) or {}
    if not isinstance(data, dict):
        data = {}
    lang_block = data.get("languages")
    if not isinstance(lang_block, dict):
        lang_block = {}
    supported = set(analysis_config.LANGUAGE_CONFIG.keys())
    for language in supported:
        entry = lang_block.get(language)
        if not isinstance(entry, dict):
            entry = {}
        entry["enabled"] = language in selected
        lang_block[language] = entry
    data["languages"] = lang_block
    cfg_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def supported_languages() -> list[str]:
    return sorted(analysis_config.LANGUAGE_CONFIG.keys())


__all__ = ["InitDialogDefaults", "apply_language_selection", "detect_languages", "supported_languages"]
