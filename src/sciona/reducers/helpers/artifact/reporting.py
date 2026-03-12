# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Helper wrappers for artifact reporting diagnostics reads."""

from __future__ import annotations

from pathlib import Path

from ..artifact.graph_edges import load_call_resolution_diagnostics
from ..shared.context import current_artifact_connection, fallback_artifact_connection


def load_call_resolution_diagnostics_payload(
    *,
    repo_root: Path,
    snapshot_id: str,
) -> dict[str, object]:
    conn = current_artifact_connection()
    owns_connection = False
    if conn is None:
        conn = fallback_artifact_connection(repo_root)
        owns_connection = conn is not None
    if conn is None:
        return {}
    try:
        return load_call_resolution_diagnostics(
            repo_root,
            snapshot_id=snapshot_id,
        )
    finally:
        if owns_connection:
            conn.close()


__all__ = ["load_call_resolution_diagnostics_payload"]
