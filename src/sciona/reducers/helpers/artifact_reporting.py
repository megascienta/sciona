# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Helper wrappers for artifact reporting reads."""

from __future__ import annotations

from pathlib import Path
from typing import List

from ...data_storage.artifact_db import read_reporting
from .context import current_artifact_connection, fallback_artifact_connection


def load_callsite_caller_status_counts(
    *,
    repo_root: Path,
    snapshot_id: str,
) -> List[dict[str, object]]:
    conn = current_artifact_connection()
    owns_connection = False
    if conn is None:
        conn = fallback_artifact_connection(repo_root)
        owns_connection = conn is not None
    if conn is None:
        return []
    try:
        return read_reporting.call_site_caller_status_counts(
            conn,
            snapshot_id=snapshot_id,
        )
    finally:
        if owns_connection:
            conn.close()


__all__ = ["load_callsite_caller_status_counts"]

