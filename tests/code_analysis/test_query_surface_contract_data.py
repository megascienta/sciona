# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
from pathlib import Path

from sciona.code_analysis.languages.common.query import query_surface


def test_query_surface_contract_json_has_expected_languages_and_keys() -> None:
    payload = json.loads(
        Path("src/sciona/code_analysis/contracts/declarative/query_surfaces.json").read_text(
            encoding="utf-8"
        )
    )
    assert set(payload) == {"java", "javascript", "python", "typescript"}
    assert set(payload["python"]) == {
        "calls",
        "imports",
        "skip_calls",
        "structural_carriers",
        "structural_nodes",
    }


def test_query_surface_module_exports_contract_data() -> None:
    payload = json.loads(
        Path("src/sciona/code_analysis/contracts/declarative/query_surfaces.json").read_text(
            encoding="utf-8"
        )
    )
    assert tuple(payload["python"]["imports"]) == query_surface.PYTHON_IMPORT_NODE_TYPES
    assert frozenset(payload["typescript"]["structural_nodes"]) == (
        query_surface.TYPESCRIPT_STRUCTURAL_NODE_TYPES
    )
    assert tuple(payload["java"]["packages"]) == query_surface.JAVA_PACKAGE_NODE_TYPES
