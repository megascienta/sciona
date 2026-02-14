# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Prompt reducer metadata definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping, Tuple


@dataclass(frozen=True)
class ReducerMeta:
    reducer_id: str
    category: Literal[
        "discovery",
        "navigation",
        "structure",
        "relations",
        "metrics",
        "source",
    ]
    scope: Literal["callable", "class", "module", "codebase"]
    placeholders: Tuple[str, ...]
    determinism: Literal["strict", "conditional"]
    payload_size_stats: Mapping[str, object] | None
    summary: str
    lossy: bool = False
    baseline_only: bool = False


__all__ = ["ReducerMeta"]
