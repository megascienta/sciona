# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared reducer metadata constants."""

from __future__ import annotations

from typing import Literal


CATEGORY_ORDER = ("core", "grounding", "analytics", "composites")
VALID_CATEGORIES = frozenset(CATEGORY_ORDER)

SCOPE_ORDER = ("callable", "classifier", "module", "codebase")
VALID_SCOPES = frozenset(SCOPE_ORDER)

DETERMINISM_ORDER = ("strict", "conditional")
VALID_DETERMINISM = frozenset(DETERMINISM_ORDER)

INVESTIGATION_ROLE_ORDER = ("structure", "relations", "metrics", "source")
VALID_INVESTIGATION_ROLES = frozenset(INVESTIGATION_ROLE_ORDER)

RISK_TIER_ORDER = ("normal", "elevated")
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
ScopeLiteral = Literal[*SCOPE_ORDER]
DeterminismLiteral = Literal[*DETERMINISM_ORDER]
InvestigationRoleLiteral = Literal[*INVESTIGATION_ROLE_ORDER]
RiskTierLiteral = Literal[*RISK_TIER_ORDER]
InvestigationStageLiteral = Literal[*INVESTIGATION_STAGE_ORDER]

__all__ = [
    "CATEGORY_ORDER",
    "VALID_CATEGORIES",
    "VALID_SCOPES",
    "VALID_DETERMINISM",
    "INVESTIGATION_ROLE_ORDER",
    "VALID_INVESTIGATION_ROLES",
    "RISK_TIER_ORDER",
    "VALID_RISK_TIERS",
    "INVESTIGATION_STAGE_ORDER",
    "VALID_INVESTIGATION_STAGES",
    "CategoryLiteral",
    "ScopeLiteral",
    "DeterminismLiteral",
    "InvestigationRoleLiteral",
    "RiskTierLiteral",
    "InvestigationStageLiteral",
]
