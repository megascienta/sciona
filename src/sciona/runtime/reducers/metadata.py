# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared reducer metadata constants."""

from __future__ import annotations

from typing import Literal


CATEGORY_ORDER = (
    "orientation",
    "navigation",
    "coupling",
    "symbol",
    "diagnostic",
    "overlay",
    "source"
)
VALID_CATEGORIES = frozenset(CATEGORY_ORDER)

CategoryLiteral = Literal[*CATEGORY_ORDER]

__all__ = [
    "CATEGORY_ORDER",
    "VALID_CATEGORIES",
    "CategoryLiteral",
]
