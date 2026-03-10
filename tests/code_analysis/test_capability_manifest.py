# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sciona.code_analysis.languages.common.support.capability_manifest import (
    build_capability_manifest,
)

pytestmark = [pytest.mark.policy]


def test_capability_manifest_is_current() -> None:
    manifest_path = Path("docs/CAPABILITY_MANIFEST.json")
    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert on_disk == build_capability_manifest()


def test_capability_manifest_declares_typescript_dynamic_import_surface() -> None:
    manifest = build_capability_manifest()
    typescript = manifest["queries"]["typescript"]
    assert typescript["dynamic_imports"] == ["call_expression"]


def test_capability_manifest_declares_python_bound_callable_construct() -> None:
    manifest = build_capability_manifest()
    constructs = {
        entry["construct"]: entry
        for entry in manifest["walker_capabilities"]["python"]
    }
    assert "bound_callable_declaration" in constructs
    assert constructs["bound_callable_declaration"]["node_types"] == [
        "assignment",
        "augmented_assignment",
    ]


def test_capability_manifest_declares_javascript_import_and_require_surfaces() -> None:
    manifest = build_capability_manifest()
    javascript = manifest["queries"]["javascript"]
    assert javascript["dynamic_imports"] == ["call_expression"]
    assert javascript["require_declarations"] == ["lexical_declaration"]


def test_capability_manifest_declares_structural_carriers() -> None:
    manifest = build_capability_manifest()
    python = manifest["queries"]["python"]
    typescript = manifest["queries"]["typescript"]
    java = manifest["queries"]["java"]

    assert python["structural_carriers"] == ["expression_statement"]
    assert "statement_block" in typescript["structural_carriers"]
    assert java["structural_carriers"] == []
