# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Overlay computation helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from collections import Counter
from typing import Iterable

from ...code_analysis.core.extract import registry
from ...code_analysis import config as analysis_config
from ...code_analysis.core.normalize_model import FileRecord, FileSnapshot, SemanticNodeRecord
from ...code_analysis.tools.workspace import snapshots as snapshot_tools
from ...code_analysis.tools.workspace import excludes as path_excludes
from ...data_storage.core_db import read_ops as core_read
from ...runtime import config as runtime_config
from ...runtime.config import io as runtime_config_io
from ...runtime import constants as runtime_constants
from ...runtime import git as git_ops
from ...runtime import identity as ids
from ...runtime.text import canonical_span_bytes
from ...runtime import time as runtime_time
from ...runtime.errors import ConfigError
from ...runtime.logging import get_logger

from .calls import compute_call_overlay_rows

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
