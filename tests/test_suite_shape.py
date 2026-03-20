# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from pathlib import Path

import pytest


_TESTS_ROOT = Path(__file__).resolve().parent
_MIN_FILES_BY_AREA = {
    "api": 3,
    "contracts": 3,
    "cli": 8,
    "code_analysis": 22,
    "data_storage": 8,
    "pipelines": 10,
    "reducers": 6,
    "runtime": 8,
}
pytestmark = [pytest.mark.policy]


def _test_files(area: str) -> list[Path]:
    return sorted((_TESTS_ROOT / area).glob("test_*.py"))


def test_suite_shape_preserves_area_coverage() -> None:
    counts = {area: len(_test_files(area)) for area in _MIN_FILES_BY_AREA}
    for area, min_count in _MIN_FILES_BY_AREA.items():
        assert counts[area] >= min_count, (
            f"{area} has {counts[area]} test files; expected at least {min_count}. "
            "If this was intentional, update tests/test_suite_shape.py."
        )


def test_suite_shape_total_test_file_floor() -> None:
    total = sum(len(_test_files(area)) for area in _MIN_FILES_BY_AREA)
    assert total >= 70, (
        f"Total test files across core areas dropped to {total}. "
        "If this was intentional, update tests/test_suite_shape.py."
    )
