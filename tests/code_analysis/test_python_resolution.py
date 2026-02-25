# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.code_analysis.core.extract.languages.python_resolution import (
    collect_class_instance_map,
    collect_module_instance_map,
)
from sciona.code_analysis.core.extract.utils import find_nodes_of_type
from sciona.code_analysis.core.normalize.model import FileRecord, FileSnapshot
from sciona.code_analysis.tools.tree_sitter import build_parser


def _snapshot(tmp_path, source: str) -> FileSnapshot:
    file_path = tmp_path / "pkg" / "mod.py"
    file_path.parent.mkdir()
    file_path.write_text(source, encoding="utf-8")
    return FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("pkg/mod.py"),
            language="python",
        ),
        file_id="file",
        blob_sha="hash",
        size=len(source.encode("utf-8")),
        line_count=source.count("\n"),
        content=source.encode("utf-8"),
    )


def test_collect_module_instance_map_skips_async_and_lambda_scopes(tmp_path) -> None:
    source = """
class A:
    pass

async def runner():
    x = A()

fn = lambda: A()
y = A()
"""
    snapshot = _snapshot(tmp_path, source)
    root = build_parser("python").parse(snapshot.content).root_node
    module_map = collect_module_instance_map(
        root,
        snapshot,
        class_name_candidates={"A": {"repo.pkg.mod.A"}},
        import_aliases={},
        member_aliases={},
        raw_module_map={},
    )
    assert module_map == {"y": "repo.pkg.mod.A"}


def test_collect_class_instance_map_skips_async_method_scope(tmp_path) -> None:
    source = """
class A:
    pass

class C:
    async def runner(self):
        self.dep = A()
"""
    snapshot = _snapshot(tmp_path, source)
    root = build_parser("python").parse(snapshot.content).root_node
    class_nodes = list(find_nodes_of_type(root, "class_definition"))
    class_body = class_nodes[1].child_by_field_name("body")
    class_map = collect_class_instance_map(
        class_body,
        snapshot,
        class_name_candidates={"A": {"repo.pkg.mod.A"}},
        import_aliases={},
        member_aliases={},
        raw_module_map={},
    )
    assert class_map == {}
