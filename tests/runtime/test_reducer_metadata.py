# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from dataclasses import fields

from sciona.runtime.reducers.metadata import (
    CATEGORY_ORDER,
    VALID_CATEGORIES,
)
from sciona.reducers.registry import ReducerEntry, get_reducers

def test_reducer_metadata_constants() -> None:
    assert CATEGORY_ORDER == ("orientation", "navigation", "coupling", "symbol", "diagnostic", "overlay", "source")
    assert set(CATEGORY_ORDER) == set(VALID_CATEGORIES)

def test_reducer_registry_exposes_category_only_metadata() -> None:
    reducers = get_reducers()
    assert reducers
    assert {field.name for field in fields(ReducerEntry)} == {
        "reducer_id",
        "category",
        "placeholder",
        "summary",
        "anomaly_detector",
        "module",
    }
    for entry in reducers.values():
        assert entry.category in VALID_CATEGORIES
        assert entry.placeholder
        assert entry.module.__name__.startswith("sciona.reducers.")
        assert ".core." not in entry.module.__name__
        assert ".analytics." not in entry.module.__name__
        assert ".grounding." not in entry.module.__name__
        assert ".composites." not in entry.module.__name__
