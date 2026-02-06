"""Overlay payload types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OverlayPayload:
    worktree_hash: str
    nodes: dict[str, list[dict[str, object]]]
    edges: dict[str, list[dict[str, object]]]
    calls: dict[str, list[dict[str, object]]]
    summary: dict[str, object] | None


__all__ = ["OverlayPayload"]
