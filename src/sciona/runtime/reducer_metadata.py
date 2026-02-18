# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared reducer metadata constants."""

from __future__ import annotations

from typing import Literal


CATEGORY_ORDER = (
    "discovery",
    "navigation",
    "structure",
    "relations",
    "metrics",
    "source",
)

VALID_CATEGORIES = frozenset(CATEGORY_ORDER)
VALID_SCOPES = frozenset(("callable", "class", "module", "codebase"))
VALID_DETERMINISM = frozenset(("strict", "conditional"))

CategoryLiteral = Literal[
    "discovery",
    "navigation",
    "structure",
    "relations",
    "metrics",
    "source",
]
ScopeLiteral = Literal["callable", "class", "module", "codebase"]
DeterminismLiteral = Literal["strict", "conditional"]

__all__ = [
    "CATEGORY_ORDER",
    "VALID_CATEGORIES",
    "VALID_SCOPES",
    "VALID_DETERMINISM",
    "CategoryLiteral",
    "ScopeLiteral",
    "DeterminismLiteral",
]
