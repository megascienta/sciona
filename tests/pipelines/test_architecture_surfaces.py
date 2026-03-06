# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

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
