from sciona import reducers
from sciona.code_analysis.analysis import graph as analysis_graph


def test_analysis_graph_public_surface_is_explicit():
    expected = {"module_id_for"}
    assert set(analysis_graph.__all__) == expected


def test_structural_reducers_public_surface_exports_modules():
    expected = {
        "structural_index",
        "module_overview",
        "class_overview",
        "callable_overview",
    }
    for name in expected:
        module = getattr(reducers.structural, name)
        assert hasattr(module, "run"), f"Reducer module '{name}' must expose run()"
