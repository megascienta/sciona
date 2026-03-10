# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Reducer-facing profile helpers."""

from __future__ import annotations

from ....code_analysis.tools.profiling import (
    java_class_extras,
    java_function_extras,
    python_class_extras,
    python_function_extras,
    typescript_class_extras,
    typescript_function_extras,
)


def fetch_node_instance(conn, snapshot_id: str, structural_id: str) -> dict:
    """Return structural + instance metadata for the requested node."""
    row = conn.execute(
        """
        SELECT
            sn.structural_id,
            sn.node_type,
            sn.language,
            ni.qualified_name,
            ni.file_path,
            ni.start_line,
            ni.end_line,
            ni.start_byte,
            ni.end_byte,
            ni.content_hash
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE sn.structural_id = ? AND ni.snapshot_id = ?
        LIMIT 1
        """,
        (structural_id, snapshot_id),
    ).fetchone()
    if not row:
        raise ValueError(
            f"Node '{structural_id}' not found in snapshot '{snapshot_id}'."
        )
    return row


__all__ = [
    "fetch_node_instance",
    "java_class_extras",
    "java_function_extras",
    "python_class_extras",
    "python_function_extras",
    "typescript_class_extras",
    "typescript_function_extras",
]
