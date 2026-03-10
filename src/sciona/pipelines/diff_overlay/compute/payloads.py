# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Overlay computation helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from collections import Counter
from typing import Iterable

from ....code_analysis.core.extract import registry
from ....code_analysis import config as analysis_config
from ....code_analysis.core.normalize_model import (
    FileRecord,
    FileSnapshot,
    SemanticNodeRecord,
)
from ....code_analysis.tools.workspace import snapshots as snapshot_tools
from ....code_analysis.tools.workspace import excludes as path_excludes
from ....data_storage.core_db import read_ops as core_read
from ....runtime import config as runtime_config
from ....runtime.config import io as runtime_config_io
from ....runtime import constants as runtime_constants
from ....runtime import git as git_ops
from ....runtime import identity as ids
from ....runtime.text import canonical_span_bytes
from ....runtime import time as runtime_time
from ....runtime.errors import ConfigError
from ....runtime.logging import get_logger

from ..calls import compute_call_overlay_rows

def node_payload(node: SemanticNodeRecord, file_snapshot: FileSnapshot) -> dict[str, object]:
    structural_id = ids.structural_id(
        node.node_type, node.language, node.qualified_name
    )
    return {
        "structural_id": structural_id,
        "node_type": node.node_type,
        "language": node.language,
        "qualified_name": node.qualified_name,
        "file_path": node.file_path.as_posix(),
        "start_line": node.start_line,
        "end_line": node.end_line,
        "content_hash": node_content_hash(node, file_snapshot),
    }

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

def edge_payload(edge) -> dict[str, object]:
    src_id = ids.structural_id(
        edge.src_node_type, edge.src_language, edge.src_qualified_name
    )
    dst_id = ids.structural_id(
        edge.dst_node_type, edge.dst_language, edge.dst_qualified_name
    )
    return {
        "src_structural_id": src_id,
        "dst_structural_id": dst_id,
        "edge_type": edge.edge_type,
    }

def edge_key(src_id: str, dst_id: str, edge_type: str) -> str:
    return hashlib.sha1(f"{src_id}:{dst_id}:{edge_type}".encode("utf-8")).hexdigest()

def overlay_row(
    snapshot_id: str,
    structural_id: str,
    node_type: str,
    *,
    diff_kind: str,
    created_at: str,
    worktree_hash: str,
    field: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
) -> dict[str, object]:
    return {
        "snapshot_id": snapshot_id,
        "worktree_hash": worktree_hash,
        "structural_id": structural_id,
        "node_type": node_type,
        "diff_kind": diff_kind,
        "field": field,
        "old_value": old_value,
        "new_value": new_value,
        "created_at": created_at,
    }
