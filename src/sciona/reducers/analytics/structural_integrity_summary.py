# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Structural integrity diagnostics reducer."""

from __future__ import annotations

from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="structural_integrity_summary",
    category="analytics",
    scope="codebase",
    placeholders=("STRUCTURAL_INTEGRITY_SUMMARY",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Structural integrity diagnostics over committed SCI facts. "
    "Use to detect duplicates, lexical orphans, and inheritance-cycle anomalies before downstream reasoning. "
    "Scope: codebase-level. Payload kind: summary.",
    lossy=True,
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    top_k: int = 25,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="structural_integrity_summary reducer"
    )
    limit = _normalize_limit(top_k)
    duplicates = _duplicate_qualified_names(conn, snapshot_id, limit=limit)
    lexical_orphans = _lexical_orphans(conn, snapshot_id, limit=limit)
    inheritance_cycles = _inheritance_cycles(conn, snapshot_id, limit=limit)
    body = {
        "payload_kind": "summary",
        "top_k": limit,
        "integrity_ok": not duplicates and not lexical_orphans and not inheritance_cycles,
        "duplicate_qualified_names": duplicates,
        "duplicate_qualified_name_count": len(duplicates),
        "lexical_orphans": lexical_orphans,
        "lexical_orphan_count": len(lexical_orphans),
        "inheritance_cycles": inheritance_cycles,
        "inheritance_cycle_count": len(inheritance_cycles),
    }
    return render_json_payload(body)


def _normalize_limit(top_k: int) -> int:
    value = int(top_k)
    if value <= 0:
        raise ValueError("structural_integrity_summary top_k must be positive.")
    return value


def _duplicate_qualified_names(conn, snapshot_id: str, *, limit: int) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT ni.qualified_name, sn.node_type, sn.language, COUNT(*) AS duplicate_count
        FROM node_instances ni
        JOIN structural_nodes sn ON sn.structural_id = ni.structural_id
        WHERE ni.snapshot_id = ?
        GROUP BY ni.qualified_name, sn.node_type, sn.language
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC, ni.qualified_name, sn.node_type, sn.language
        LIMIT ?
        """,
        (snapshot_id, limit),
    ).fetchall()
    return [
        {
            "qualified_name": row["qualified_name"],
            "node_type": row["node_type"],
            "language": row["language"],
            "count": int(row["duplicate_count"] or 0),
        }
        for row in rows
    ]


def _lexical_orphans(conn, snapshot_id: str, *, limit: int) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT sn.structural_id, sn.node_type, sn.language, ni.qualified_name, ni.file_path
        FROM structural_nodes sn
        JOIN node_instances ni
          ON ni.structural_id = sn.structural_id
         AND ni.snapshot_id = ?
        WHERE sn.node_type IN ('type', 'callable')
          AND NOT EXISTS (
              SELECT 1
              FROM edges e
              JOIN structural_nodes parent ON parent.structural_id = e.src_structural_id
              WHERE e.snapshot_id = ni.snapshot_id
                AND e.dst_structural_id = sn.structural_id
                AND e.edge_type = 'LEXICALLY_CONTAINS'
                AND parent.node_type IN ('module', 'type')
          )
        ORDER BY ni.qualified_name, sn.structural_id
        LIMIT ?
        """,
        (snapshot_id, limit),
    ).fetchall()
    return [
        {
            "structural_id": row["structural_id"],
            "node_type": row["node_type"],
            "language": row["language"],
            "qualified_name": row["qualified_name"],
            "file_path": row["file_path"],
        }
        for row in rows
    ]


def _inheritance_cycles(conn, snapshot_id: str, *, limit: int) -> list[dict[str, object]]:
    two_node_rows = conn.execute(
        """
        SELECT
            e1.src_structural_id AS class_a,
            e1.dst_structural_id AS class_b,
            a.qualified_name AS class_a_name,
            b.qualified_name AS class_b_name
        FROM edges e1
        JOIN edges e2
          ON e2.snapshot_id = e1.snapshot_id
         AND e2.src_structural_id = e1.dst_structural_id
         AND e2.dst_structural_id = e1.src_structural_id
         AND e2.edge_type IN ('EXTENDS', 'IMPLEMENTS')
        JOIN node_instances a
          ON a.structural_id = e1.src_structural_id
         AND a.snapshot_id = e1.snapshot_id
        JOIN node_instances b
          ON b.structural_id = e1.dst_structural_id
         AND b.snapshot_id = e1.snapshot_id
        WHERE e1.snapshot_id = ?
          AND e1.edge_type IN ('EXTENDS', 'IMPLEMENTS')
          AND e1.src_structural_id < e1.dst_structural_id
        ORDER BY class_a_name, class_b_name
        LIMIT ?
        """,
        (snapshot_id, limit),
    ).fetchall()
    self_rows = conn.execute(
        """
        SELECT e.src_structural_id AS class_a, i.qualified_name AS class_a_name
        FROM edges e
        JOIN node_instances i
          ON i.structural_id = e.src_structural_id
         AND i.snapshot_id = e.snapshot_id
        WHERE e.snapshot_id = ?
          AND e.edge_type IN ('EXTENDS', 'IMPLEMENTS')
          AND e.src_structural_id = e.dst_structural_id
        ORDER BY class_a_name
        LIMIT ?
        """,
        (snapshot_id, limit),
    ).fetchall()
    payload: list[dict[str, object]] = [
        {
            "cycle_type": "two_node",
            "class_a_id": row["class_a"],
            "class_b_id": row["class_b"],
            "class_a_name": row["class_a_name"],
            "class_b_name": row["class_b_name"],
        }
        for row in two_node_rows
    ]
    payload.extend(
        {
            "cycle_type": "self",
            "class_a_id": row["class_a"],
            "class_b_id": row["class_a"],
            "class_a_name": row["class_a_name"],
            "class_b_name": row["class_a_name"],
        }
        for row in self_rows
    )
    payload.sort(
        key=lambda item: (
            str(item.get("cycle_type")),
            str(item.get("class_a_name")),
            str(item.get("class_b_name")),
        )
    )
    return payload[:limit]


__all__ = ["render", "REDUCER_META"]
