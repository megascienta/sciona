# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Snapshot lifecycle semantics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SnapshotLifecycle(str, Enum):
    REUSED = "reused"
    COMMITTED = "committed"


@dataclass(frozen=True)
class SnapshotDecision:
    lifecycle: SnapshotLifecycle
    snapshot_id: str
    structural_hash: Optional[str] = None
    reason: Optional[str] = None


__all__ = ["SnapshotDecision", "SnapshotLifecycle"]
