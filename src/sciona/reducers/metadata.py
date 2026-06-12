# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Prompt reducer metadata definitions."""

from __future__ import annotations

from dataclasses import dataclass

from ..runtime.reducers.metadata import (
    CategoryLiteral,
)


@dataclass(frozen=True)
class ReducerArg:
    name: str
    type: str
    description: str
    required: bool = False
    enum: tuple[str, ...] = ()
    default: str | None = None


@dataclass(frozen=True)
class ReducerMeta:
    reducer_id: str
    category: CategoryLiteral
    placeholder: str
    summary: str
    anomaly_detector: bool = False
    args: tuple[ReducerArg, ...] = ()
    requires: str | None = None


__all__ = ["ReducerArg", "ReducerMeta"]
