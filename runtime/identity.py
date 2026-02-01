"""Deterministic identifier utilities."""
from __future__ import annotations

import hashlib


def structural_id(node_type: str, language: str, qualified_name: str) -> str:
    """Return a stable structural identifier."""
    payload = f"{node_type}:{language}:{qualified_name}".encode("utf-8")
    return hashlib.sha1(payload).hexdigest()


def instance_id(snapshot_id: str, structural_id_value: str) -> str:
    return f"{snapshot_id}:{structural_id_value}"
