"""Prompt reducer metadata definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Tuple


@dataclass(frozen=True)
class ReducerMeta:
    reducer_id: str
    scope: str
    placeholders: Tuple[str, ...]
    determinism: str
    payload_size_stats: Mapping[str, object] | None
    semantic_tag: str
    summary: str
    lossy: bool = False
    baseline_only: bool = False
    composite: bool = False


__all__ = ["ReducerMeta"]
