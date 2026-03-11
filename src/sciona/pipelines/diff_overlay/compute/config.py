# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Overlay computation helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ....code_analysis.core.extract import registry
from ....code_analysis import config as analysis_config
from ....runtime import config as runtime_config
from ....runtime.config import io as runtime_config_io
from ....runtime.common import constants as runtime_constants
from ....runtime import git as git_ops
from ....runtime.errors import ConfigError

def resolve_enabled_languages(repo_root: Path) -> list[str]:
    try:
        settings = runtime_config.load_language_settings(repo_root)
        enabled = [name for name, config in settings.items() if config.enabled]
        if enabled:
            return enabled
        return sorted(analysis_config.LANGUAGE_CONFIG.keys())
    except ConfigError:
        return sorted(analysis_config.LANGUAGE_CONFIG.keys())

def discovery_excludes(repo_root: Path) -> list[str]:
    try:
        return list(runtime_config.load_discovery_settings(repo_root).exclude_globs)
    except ConfigError:
        return []

def analyzers_by_language() -> dict[str, object]:
    analyzers: dict[str, object] = {}
    for language in analysis_config.LANGUAGE_CONFIG.keys():
        analyzer = registry.get_analyzer(language)
        if analyzer:
            analyzers[language] = analyzer
    return analyzers


def worktree_fingerprint(
    repo_root: Path,
    base_commit: str,
    *,
    cache: dict[tuple[Path, tuple[str, ...], str | None], str],
) -> str:
    parts = []
    parts.append(
        git_ops.git_output(
            repo_root,
            ["diff", "--name-status", base_commit],
            cache=cache,
        )
    )
    parts.append(
        git_ops.git_output(
            repo_root,
            ["diff", "--cached", "--name-status", base_commit],
            cache=cache,
        )
    )
    parts.append(
        git_ops.git_output(
            repo_root,
            ["ls-files", "--others", "--exclude-standard"],
            cache=cache,
        )
    )
    config_text = runtime_config_io.load_config_text(repo_root) or ""
    parts.append(config_text)
    parts.append(runtime_constants.TOOL_VERSION)
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
