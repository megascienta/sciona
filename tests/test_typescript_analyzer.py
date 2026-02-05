from pathlib import Path

from sciona.code_analysis.core.extract.languages.typescript import TypeScriptAnalyzer
from sciona.code_analysis.core.normalize.model import FileRecord, FileSnapshot
from sciona.runtime import paths as runtime_paths


def test_typescript_analyzer_extracts_structure(tmp_path):
    module = """
    import { helper } from './utils.js';
    export class Foo {
      bar() {
        helper();
      }
    }
    export function helper() {}
    """
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "mod.ts"
    file_path.write_text(module, encoding="utf-8")
    record = FileRecord(
        path=file_path,
        relative_path=Path("src/mod.ts"),
        language="typescript",
    )
    snapshot = FileSnapshot(
        record=record,
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = TypeScriptAnalyzer()
    result = analyzer.analyze(snapshot, "src.mod")
    node_types = {node.node_type for node in result.nodes}
    assert {"module", "class", "function", "method"}.issubset(node_types)
    import_edges = [edge for edge in result.edges if edge.edge_type == "IMPORTS_DECLARED"]
    assert import_edges
    imported = {edge.dst_qualified_name for edge in import_edges}
    repo_prefix = runtime_paths.repo_name_prefix(repo)
    assert f"{repo_prefix}.src.utils" in imported, imported
    assert not [edge for edge in result.edges if edge.edge_type == "CALLS"]
    method_edges = [edge for edge in result.edges if edge.edge_type == "DEFINES_METHOD"]
    assert method_edges and method_edges[0].src_node_type == "class"
