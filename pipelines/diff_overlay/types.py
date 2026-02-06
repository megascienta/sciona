"""Overlay payload types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OverlayPayload:
    worktree_hash: str
    snapshot_commit: str | None
    base_commit: str | None
    head_commit: str | None
    merge_base: str | None
    nodes: dict[str, list[dict[str, object]]]
    edges: dict[str, list[dict[str, object]]]
    calls: dict[str, list[dict[str, object]]]
    summary: dict[str, object] | None
    warnings: list[str]


__all__ = ["OverlayPayload"]
