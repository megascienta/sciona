# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Connection configuration helpers shared by storage connection lifecycles."""

from __future__ import annotations

import os
from pathlib import Path

from ...runtime import config as runtime_config
from ...runtime.config import defaults


def resolve_db_timeout(repo_root: Path | None) -> float:
    env_override = os.getenv("SCIONA_DB_TIMEOUT")
    if env_override:
        try:
            return float(env_override)
        except ValueError:
            pass
    if repo_root is not None:
        try:
            settings = runtime_config.load_runtime_config(repo_root).database
            return float(settings.timeout)
        except Exception:
            pass
    return float(defaults.DEFAULT_DB_TIMEOUT)
