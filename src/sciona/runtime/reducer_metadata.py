# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared reducer metadata constants."""

from __future__ import annotations

from typing import Literal


CATEGORY_ORDER = (
    "structure",
    "relations",
    "metrics",
    "source"
)
VALID_CATEGORIES = frozenset(CATEGORY_ORDER)

RISK_TIER_ORDER = (
    "normal",
    "elevated"
)
VALID_RISK_TIERS = frozenset(RISK_TIER_ORDER)

INVESTIGATION_STAGE_ORDER = (
    "initial_scan",
    "entity_discovery",
    "structure_inspection",
    "relationship_analysis",
    "diagnostics_metrics",
    "source_verification",
)
VALID_INVESTIGATION_STAGES = frozenset(INVESTIGATION_STAGE_ORDER)

CategoryLiteral = Literal[*CATEGORY_ORDER]
RiskTierLiteral = Literal[*RISK_TIER_ORDER]
InvestigationStageLiteral = Literal[*INVESTIGATION_STAGE_ORDER]

__all__ = [
    "CATEGORY_ORDER",
    "VALID_CATEGORIES",
    "RISK_TIER_ORDER",
    "VALID_RISK_TIERS",
    "INVESTIGATION_STAGE_ORDER",
    "VALID_INVESTIGATION_STAGES",
    "CategoryLiteral",
    "RiskTierLiteral",
    "InvestigationStageLiteral",
]
