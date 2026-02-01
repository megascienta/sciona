"""Deterministic hashing for snapshot structural state."""
from __future__ import annotations

import hashlib
from typing import Iterable


def compute_structural_hash(conn, snapshot_id: str) -> str:
    """Return a canonical hash for the given snapshot's structural state."""
    entries = []
    entries.extend(_node_rows(conn, snapshot_id))
    entries.extend(_edge_rows(conn, snapshot_id))
    payload = "\n".join(entries).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _node_rows(conn, snapshot_id: str) -> Iterable[str]:
    rows = conn.execute(
        """
        SELECT sn.structural_id,
               sn.node_type,
               sn.language,
               ni.qualified_name,
               ni.file_path,
               ni.start_line,
               ni.end_line,
               ni.content_hash
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
        ORDER BY sn.structural_id ASC
        """,
        (snapshot_id,),
    ).fetchall()
    for row in rows:
        yield "|".join(
            [
                "N",
                row["structural_id"],
                row["node_type"],
                row["language"],
                row["qualified_name"],
                row["file_path"],
                str(row["start_line"]),
                str(row["end_line"]),
                row["content_hash"],
            ]
        )


def _edge_rows(conn, snapshot_id: str) -> Iterable[str]:
    rows = conn.execute(
        """
        SELECT snapshot_id,
               src_structural_id,
               dst_structural_id,
               edge_type
        FROM edges
        WHERE snapshot_id = ?
        ORDER BY src_structural_id ASC, dst_structural_id ASC, edge_type ASC
        """,
        (snapshot_id,),
    ).fetchall()
    for row in rows:
        yield "|".join(
            [
                "E",
                row["src_structural_id"],
                row["dst_structural_id"],
                row["edge_type"],
            ]
        )
