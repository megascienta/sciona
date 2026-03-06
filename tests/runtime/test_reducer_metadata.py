# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.runtime.reducer_metadata import (
    CATEGORY_ORDER,
    DETERMINISM_ORDER,
    INVESTIGATION_STAGE_ORDER,
    INVESTIGATION_ROLE_ORDER,
    RISK_TIER_ORDER,
    SCOPE_ORDER,
    VALID_CATEGORIES,
    VALID_DETERMINISM,
    VALID_INVESTIGATION_STAGES,
    VALID_INVESTIGATION_ROLES,
    VALID_RISK_TIERS,
    VALID_SCOPES,
)
from sciona.reducers.registry import get_reducers


def test_reducer_metadata_constants() -> None:
    assert CATEGORY_ORDER[:3] == ("core", "grounding", "analytics")
    assert "composites" in CATEGORY_ORDER
    assert set(CATEGORY_ORDER) == set(VALID_CATEGORIES)
    assert SCOPE_ORDER == ("callable", "classifier", "module", "codebase")
    assert set(SCOPE_ORDER) == set(VALID_SCOPES)
    assert DETERMINISM_ORDER == ("strict", "conditional")
    assert set(DETERMINISM_ORDER) == set(VALID_DETERMINISM)
    assert INVESTIGATION_ROLE_ORDER == ("structure", "relations", "metrics", "source")
    assert set(INVESTIGATION_ROLE_ORDER) == set(VALID_INVESTIGATION_ROLES)
    assert RISK_TIER_ORDER == ("normal", "elevated")
    assert set(RISK_TIER_ORDER) == set(VALID_RISK_TIERS)
    assert INVESTIGATION_STAGE_ORDER == (
        "initial_scan",
        "entity_discovery",
        "structure_inspection",
        "relationship_analysis",
        "diagnostics_metrics",
        "source_verification",
    )
    assert set(INVESTIGATION_STAGE_ORDER) == set(VALID_INVESTIGATION_STAGES)


def test_reducer_registry_exposes_explicit_risk_and_stage() -> None:
    reducers = get_reducers()
    assert reducers
    for entry in reducers.values():
        assert entry.risk_tier in VALID_RISK_TIERS
        assert entry.investigation_stage in VALID_INVESTIGATION_STAGES
