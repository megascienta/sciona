# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Prompt reducer metadata definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Tuple

from ..runtime.reducer_metadata import (
    CategoryLiteral,
    DeterminismLiteral,
    ScopeLiteral,
)


@dataclass(frozen=True)
class ReducerMeta:
    reducer_id: str
    category: CategoryLiteral
    scope: ScopeLiteral
    placeholders: Tuple[str, ...]
    determinism: DeterminismLiteral
    payload_size_stats: Mapping[str, object] | None
    summary: str
    lossy: bool = False
    baseline_only: bool = False


__all__ = ["ReducerMeta"]
