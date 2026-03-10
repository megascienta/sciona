# SPDX-License-Identifier: MIT

from sciona.code_analysis.core.normalize_model import EdgeRecord
from sciona.code_analysis.core.structural_assembler_index import (
    build_import_targets,
    expand_import_targets,
)


def test_expand_import_targets_computes_transitive_closure() -> None:
    direct = {
        "pkg.cli.main": {"pkg.api.cli"},
        "pkg.api.cli": {"pkg.runtime.paths"},
        "pkg.runtime.paths": set(),
    }
    expanded = expand_import_targets(direct)
    assert expanded["pkg.cli.main"] == {"pkg.api.cli", "pkg.runtime.paths"}
    assert expanded["pkg.api.cli"] == {"pkg.runtime.paths"}
    assert expanded["pkg.runtime.paths"] == set()


def test_build_import_targets_returns_direct_targets() -> None:
    edges = [
        EdgeRecord(
            src_language="python",
            src_node_type="module",
            src_qualified_name="pkg.cli.main",
            dst_language="python",
            dst_node_type="module",
            dst_qualified_name="pkg.api.cli",
            edge_type="IMPORTS_DECLARED",
            confidence=1.0,
        ),
        EdgeRecord(
            src_language="python",
            src_node_type="module",
            src_qualified_name="pkg.api.cli",
            dst_language="python",
            dst_node_type="module",
            dst_qualified_name="pkg.runtime.paths",
            edge_type="IMPORTS_DECLARED",
            confidence=1.0,
        ),
        EdgeRecord(
            src_language="python",
            src_node_type="module",
            src_qualified_name="pkg.cli.main",
            dst_language="python",
            dst_node_type="callable",
            dst_qualified_name="pkg.runtime.paths.get_repo_root",
            edge_type="CALLABLE_IMPORTS_DECLARED",
            confidence=1.0,
        ),
    ]
    targets = build_import_targets(edges)
    assert targets["pkg.cli.main"] == {"pkg.api.cli"}
    expanded = expand_import_targets(targets)
    assert expanded["pkg.cli.main"] == {"pkg.api.cli", "pkg.runtime.paths"}
