# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Prompt reducer metadata definitions."""

from __future__ import annotations

from dataclasses import dataclass

from ..runtime.reducers.metadata import (
    CategoryLiteral,
)


@dataclass(frozen=True)
class ReducerMeta:
    reducer_id: str
    category: CategoryLiteral
    placeholder: str
    summary: str
    anomaly_detector: bool = False


__all__ = ["ReducerMeta"]
