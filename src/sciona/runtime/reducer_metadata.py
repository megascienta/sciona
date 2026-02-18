# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared reducer metadata constants."""

from __future__ import annotations

from typing import Literal


CATEGORY_ORDER = ("core", "grounding", "analytics")
VALID_CATEGORIES = frozenset(CATEGORY_ORDER)

SCOPE_ORDER = ("callable", "class", "module", "codebase")
VALID_SCOPES = frozenset(SCOPE_ORDER)

DETERMINISM_ORDER = ("strict", "conditional")
VALID_DETERMINISM = frozenset(DETERMINISM_ORDER)

CategoryLiteral = Literal[*CATEGORY_ORDER]
ScopeLiteral = Literal[*SCOPE_ORDER]
DeterminismLiteral = Literal[*DETERMINISM_ORDER]

__all__ = [
    "CATEGORY_ORDER",
    "VALID_CATEGORIES",
    "VALID_SCOPES",
    "VALID_DETERMINISM",
    "CategoryLiteral",
    "ScopeLiteral",
    "DeterminismLiteral",
]
