# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Target-shaping helpers for call extraction."""

from __future__ import annotations

from typing import Sequence

from .call_extraction_types import (
    CallTarget,
    CallTargetIR,
    QualifiedCallIR,
    ReceiverCallIR,
    TerminalCallIR,
)


def _callee_text(node, content: bytes) -> str | None:
    if node is None:
        return None
    text = getattr(node, "text", None)
    if text:
        return text.decode("utf-8")
    return content[node.start_byte : node.end_byte].decode("utf-8")


def _normalize_callee_text(text: str | None, *, language_name: str | None = None) -> str | None:
    if not text:
        return text
    normalized = text.strip()
    if language_name in {"typescript", "javascript"}:
        normalized = normalized.replace("?.", ".")
        normalized = normalized.replace("!.", ".")
    if language_name == "java":
        normalized = normalized.replace("::", ".")
    return normalized


def _callee_shape(
    callee_text: str | None,
) -> tuple[str | None, tuple[str, ...], str]:
    if not callee_text or "." not in callee_text:
        return None, (), "unqualified"
    head = callee_text.rsplit(".", 1)[0].strip()
    chain = tuple(part for part in head.split(".") if part)
    if not chain:
        return None, (), "unqualified"
    kind = "member"
    if chain[0] in {"self", "cls", "this", "super"}:
        kind = "receiver"
    return chain[0], chain, kind


def _call_target_ir(
    terminal: str,
    callee_text: str | None,
    receiver_chain: tuple[str, ...],
    callee_kind: str,
) -> CallTargetIR:
    if not callee_text or "." not in callee_text:
        return TerminalCallIR(terminal=terminal)
    parts = tuple(part for part in callee_text.split(".") if part)
    if len(parts) < 2:
        return TerminalCallIR(terminal=terminal)
    if callee_kind == "receiver":
        return ReceiverCallIR(receiver_chain=receiver_chain, terminal=terminal)
    return QualifiedCallIR(parts=parts, terminal=terminal)


def _first_child(node):
    children = getattr(node, "children", [])
    return children[0] if children else None


def _dedupe_targets(targets: Sequence[CallTarget]) -> tuple[CallTarget, ...]:
    seen: set[tuple[str, str | None]] = set()
    ordered: list[CallTarget] = []
    for target in targets:
        key = (target.terminal, target.callee_text)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(target)
    return tuple(ordered)


__all__ = [
    "_call_target_ir",
    "_callee_shape",
    "_callee_text",
    "_dedupe_targets",
    "_first_child",
    "_normalize_callee_text",
]
