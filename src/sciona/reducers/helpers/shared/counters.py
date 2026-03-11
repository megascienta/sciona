# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Counter helpers shared by reducers."""

from __future__ import annotations

from collections import Counter


def top_modules(counter: Counter, *, limit: int) -> list[tuple[str, int]]:
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]


__all__ = ["top_modules"]
