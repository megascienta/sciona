# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.runtime.reducers.metadata import (
    CATEGORY_ORDER,
    INVESTIGATION_STAGE_ORDER,
    RISK_TIER_ORDER,
    VALID_CATEGORIES,
    VALID_INVESTIGATION_STAGES,
    VALID_RISK_TIERS,
)
from sciona.reducers.registry import get_reducers


def test_reducer_metadata_constants() -> None:
    assert CATEGORY_ORDER == ("structure", "relations", "metrics", "source")
    assert set(CATEGORY_ORDER) == set(VALID_CATEGORIES)
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
        assert entry.category in VALID_CATEGORIES
        assert entry.risk_tier in VALID_RISK_TIERS
        assert entry.stage in VALID_INVESTIGATION_STAGES
        assert entry.placeholder
        assert entry.module.__name__.startswith("sciona.reducers.")
        assert ".core." not in entry.module.__name__
        assert ".analytics." not in entry.module.__name__
        assert ".grounding." not in entry.module.__name__
        assert ".composites." not in entry.module.__name__
