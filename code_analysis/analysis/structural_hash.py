"""Deterministic hashing for snapshot structural state."""
from __future__ import annotations

import hashlib

from ...data_storage.core_db import read_ops as core_read


def compute_structural_hash(conn, snapshot_id: str) -> str:
    """Return a canonical hash for the given snapshot's structural state."""
    entries = []
    entries.extend(core_read.structural_hash_node_entries(conn, snapshot_id))
    entries.extend(core_read.structural_hash_edge_entries(conn, snapshot_id))
    payload = "\n".join(entries).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
