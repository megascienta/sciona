# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Rollback policies for coordinating error handling."""

from __future__ import annotations

from enum import Enum


class RollbackPolicy(str, Enum):
    NONE = "none"
    CORE_ONLY = "core_only"
    PAIR_REQUIRED = "pair_required"


__all__ = ["RollbackPolicy"]
