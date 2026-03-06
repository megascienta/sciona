# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Prompt reducer metadata definitions."""

from __future__ import annotations

from dataclasses import dataclass

from ..runtime.reducer_metadata import (
    CategoryLiteral,
    InvestigationStageLiteral,
    RiskTierLiteral,
)


@dataclass(frozen=True)
class ReducerMeta:
    reducer_id: str
    category: CategoryLiteral
    placeholder: str
    risk_tier: RiskTierLiteral
    stage: InvestigationStageLiteral
    summary: str
    anomaly_detector: bool = False


__all__ = ["ReducerMeta"]
