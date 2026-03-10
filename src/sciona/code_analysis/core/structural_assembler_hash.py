# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Content-hash helper for StructuralAssembler."""

from __future__ import annotations

import hashlib

from ...runtime.text import canonical_span_bytes
from .normalize_model import FileSnapshot, SemanticNodeRecord


def node_content_hash(node: SemanticNodeRecord, file_snapshot: FileSnapshot) -> str:
    content = file_snapshot.content
    if (
        node.start_byte is not None
        and node.end_byte is not None
        and 0 <= node.start_byte <= node.end_byte
        and node.end_byte <= len(content)
    ):
        segment = content[node.start_byte : node.end_byte]
        if segment:
            canonical = canonical_span_bytes(segment)
            if canonical:
                return hashlib.sha1(canonical).hexdigest()
    return file_snapshot.blob_sha


__all__ = ["node_content_hash"]
