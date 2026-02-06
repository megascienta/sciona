# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Repository setup and versioning helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from ..runtime import constants
from ..runtime.errors import (
    CorruptVersionFileError,
    NotInitializedError,
    SchemaMismatchError,
)


def write_version_file(sciona_dir: Path) -> None:
    """Create the version file with the current tool metadata."""
    sciona_dir.mkdir(parents=True, exist_ok=True)
    version_file = sciona_dir / constants.VERSION_FILENAME
    data = {
        "tool_version": constants.TOOL_VERSION,
        "schema_version": constants.SCHEMA_VERSION,
    }
    version_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def read_version_file(sciona_dir: Path) -> Dict[str, Any]:
    version_file = sciona_dir / constants.VERSION_FILENAME
    if not version_file.exists():
        raise NotInitializedError("SCIONA repository has not been initialized.")
    try:
        return json.loads(version_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CorruptVersionFileError("version.json is corrupted.") from exc


def ensure_schema_version(
    version_info: Dict[str, Any], repo_root: Path | None = None
) -> None:
    schema_version = version_info.get("schema_version")
    if schema_version == constants.SCHEMA_VERSION:
        return
    message = "SCIONA schema version mismatch. Remove the .sciona directory and run 'sciona init' to rebuild state."
    raise SchemaMismatchError(message)


def require_initialized(repo_root: Path) -> Path:
    sciona_dir = repo_root / constants.SCIONA_DIR_NAME
    if not sciona_dir.exists():
        raise NotInitializedError("Run 'sciona init' inside this repository first.")
    read_version_file(sciona_dir)
    return sciona_dir


__all__ = [
    "ensure_schema_version",
    "read_version_file",
    "require_initialized",
    "write_version_file",
]
