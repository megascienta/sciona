# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Deterministic lexical sibling-name disambiguation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LexicalNameDisambiguator:
    """Assign deterministic canonical child names per lexical parent + node kind."""

    _counts: dict[tuple[str, str, str], int] = field(default_factory=dict)
    collisions_detected: int = 0
    collisions_disambiguated: int = 0

    def canonical_name(
        self, *, parent: str, child_kind: str, local_name: str
    ) -> str:
        key = (parent, child_kind, local_name)
        occurrence = self._counts.get(key, 0) + 1
        self._counts[key] = occurrence
        if occurrence == 1:
            return local_name
        self.collisions_detected += 1
        self.collisions_disambiguated += 1
        return f"{local_name}-{occurrence}"


__all__ = ["LexicalNameDisambiguator"]
