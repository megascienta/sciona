# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared SCIONA constants."""

from __future__ import annotations

TOOL_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"
SCIONA_DIR_NAME = ".sciona"
VERSION_FILENAME = "version.json"
DB_FILENAME = "sciona.db"
ARTIFACT_DB_FILENAME = "sciona.artifacts.db"
CONFIG_FILENAME = "config.yaml"
LOG_DIRNAME = ""
LOG_FILENAME = "sciona.log"

__all__ = [
    "TOOL_VERSION",
    "SCHEMA_VERSION",
    "SCIONA_DIR_NAME",
    "VERSION_FILENAME",
    "DB_FILENAME",
    "ARTIFACT_DB_FILENAME",
    "CONFIG_FILENAME",
    "LOG_DIRNAME",
    "LOG_FILENAME",
]
