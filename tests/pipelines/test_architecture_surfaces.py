# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import ast
from pathlib import Path

from sciona import reducers
from sciona.code_analysis.analysis import graph as analysis_graph
import pytest


pytestmark = [pytest.mark.policy]


def test_analysis_graph_public_surface_is_explicit():
    expected = {"module_id_for"}
    assert set(analysis_graph.__all__) == expected


def test_structural_reducers_public_surface_exports_modules():
    expected = {
        "structural_index",
        "module_overview",
        "classifier_overview",
        "callable_overview",
    }
    for name in expected:
        module = getattr(reducers.core, name)
        assert hasattr(module, "run"), f"Reducer module '{name}' must expose run()"


def test_reducers_do_not_import_pipeline_modules_directly():
    root = Path("src/sciona/reducers")
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("sciona.pipelines") or node.module.startswith(
                    "..pipelines"
                ):
                    violations.append(f"{path}:{node.lineno}:{node.module}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("sciona.pipelines"):
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
