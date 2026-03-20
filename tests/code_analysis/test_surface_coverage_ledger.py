# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
from pathlib import Path

from sciona.code_analysis.languages.common.capabilities.walker_capabilities import (
    build_walker_capabilities,
)


def test_surface_coverage_ledger_matches_declared_constructs() -> None:
    ledger_path = Path("tests/fixtures/parity/surface_coverage.json")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    declared = {
        language: {entry["construct"] for entry in entries}
        for language, entries in build_walker_capabilities().items()
    }

    assert set(ledger) == set(declared)
    for language, constructs in declared.items():
        assert set(ledger[language]) == constructs


def test_surface_coverage_ledger_points_to_existing_canonical_suites() -> None:
    ledger = json.loads(
        Path("tests/fixtures/parity/surface_coverage.json").read_text(encoding="utf-8")
    )
    for entries in ledger.values():
        for payload in entries.values():
            suite_path = Path(payload["canonical_suite"])
            assert suite_path.exists()
