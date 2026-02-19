# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.runtime.reducer_metadata import (
    CATEGORY_ORDER,
    DETERMINISM_ORDER,
    SCOPE_ORDER,
    VALID_CATEGORIES,
    VALID_DETERMINISM,
    VALID_SCOPES,
)


def test_reducer_metadata_constants() -> None:
    assert CATEGORY_ORDER == ("core", "grounding", "analytics")
    assert set(CATEGORY_ORDER) == set(VALID_CATEGORIES)
    assert SCOPE_ORDER == ("callable", "class", "module", "codebase")
    assert set(SCOPE_ORDER) == set(VALID_SCOPES)
    assert DETERMINISM_ORDER == ("strict", "conditional")
    assert set(DETERMINISM_ORDER) == set(VALID_DETERMINISM)
