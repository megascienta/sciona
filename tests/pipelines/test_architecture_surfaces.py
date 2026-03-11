# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import ast
from pathlib import Path

from sciona import reducers
from sciona.code_analysis.analysis import module_id as analysis_module_id
import pytest


pytestmark = [pytest.mark.policy]


def test_analysis_module_id_public_surface_is_explicit():
    expected = {"module_id_for"}
    assert set(analysis_module_id.__all__) == expected


def test_reducers_public_surface_exports_modules():
    expected = {
        "call_resolution_drop_summary",
        "call_resolution_quality",
        "structural_index",
        "module_overview",
        "classifier_overview",
        "callable_overview",
        "callable_source",
        "callsite_index",
        "classifier_call_graph_summary",
        "classifier_inheritance",
        "concatenated_source",
        "dependency_edges",
        "fan_summary",
        "file_outline",
        "hotspot_summary",
        "module_call_graph_summary",
        "overlay_impact_summary",
        "overlay_projection_status_summary",
        "resolution_trace",
        "snapshot_provenance",
        "structural_integrity_summary",
        "symbol_lookup",
        "symbol_references",
    }
    for name in expected:
        module = getattr(reducers, name)
        assert hasattr(
            module, "REDUCER_META"
        ), f"Reducer module '{name}' must expose REDUCER_META"
        assert hasattr(
            module, "render"
        ), f"Reducer module '{name}' must expose render()"


def test_reducers_only_import_overlay_patching_from_pipelines():
    root = Path("src/sciona/reducers")
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("sciona.pipelines") and not node.module.startswith(
                    "sciona.pipelines.diff_overlay.patching"
                ):
                    violations.append(f"{path}:{node.lineno}:{node.module}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(
                        "sciona.pipelines"
                    ) and not alias.name.startswith(
                        "sciona.pipelines.diff_overlay.patching"
                    ):
                        violations.append(f"{path}:{node.lineno}:{alias.name}")
    assert not violations, violations


def test_runtime_does_not_import_reducer_modules():
    root = Path("src/sciona/runtime")
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("sciona.reducers") or node.module.startswith(
                    "..reducers"
                ):
                    violations.append(f"{path}:{node.lineno}:{node.module}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("sciona.reducers"):
                        violations.append(f"{path}:{node.lineno}:{alias.name}")
    assert not violations, violations
