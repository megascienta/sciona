# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Core structural analysis modules."""

from . import extract, routing
from .annotate_diff import previous_snapshot_id
from .normalize_model import AnalysisResult, EdgeRecord, FileRecord, FileSnapshot, SemanticNodeRecord
from .snapshot import Snapshot, create_snapshot, persist_snapshot
from .structural_assembler import StructuralAssembler

__all__ = [
    "extract",
    "routing",
    "previous_snapshot_id",
    "AnalysisResult",
    "EdgeRecord",
    "FileRecord",
    "FileSnapshot",
    "SemanticNodeRecord",
    "Snapshot",
    "create_snapshot",
    "persist_snapshot",
    "StructuralAssembler",
]
