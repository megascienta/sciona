import json
import sqlite3

from sciona.reducers.baseline import callable_source, concatenated_source
from sciona.reducers.structural import (
    dependency_edges,
    file_outline,
    import_references,
    module_file_map,
    symbol_lookup,
    symbol_references,
)
from sciona.reducers.summaries import callsite_index, importers_index

from tests.helpers import seed_repo_with_snapshot


def _strip_json_fence(text: str) -> str:
    trimmed = text.strip()
    if trimmed.startswith("```json") and trimmed.endswith("```"):
        lines = trimmed.splitlines()
        return "\n".join(lines[1:-1])
    return trimmed


def test_symbol_lookup_reducer_returns_matches(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    try:
        payload_text = symbol_lookup.render(
            snapshot_id,
            conn,
            repo_root,
            query="pkg.alpha",
            kind="module",
            limit=5,
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["matches"]
    assert any(match["qualified_name"] == "pkg.alpha" for match in payload["matches"])


def test_symbol_lookup_accepts_any_kind(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    try:
        payload_text = symbol_lookup.render(
            snapshot_id,
            conn,
            repo_root,
            query="pkg.alpha",
            kind="any",
            limit=5,
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["matches"]


def test_symbol_references_returns_relationships(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    try:
        payload_text = symbol_references.render(
            snapshot_id,
            conn,
            repo_root,
            query="pkg.alpha",
            kind="module",
            limit=5,
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["matches"]
    assert payload["references"]


def test_dependency_edges_reducer_returns_edges(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    try:
        payload_text = dependency_edges.render(
            snapshot_id,
            conn,
            repo_root,
            module_id="pkg.alpha",
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["edge_count"] >= 1
    edge = payload["edges"][0]
    assert "from_module_structural_id" in edge
    assert "to_module_structural_id" in edge
    assert edge["edge_source"] == "sci"


def test_dependency_edges_filters_and_limit(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    try:
        payload_text = dependency_edges.render(
            snapshot_id,
            conn,
            repo_root,
            from_module_id="pkg.alpha",
            edge_type="IMPORTS_DECLARED",
            limit=1,
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["edge_count"] == 1
    assert payload["edges"][0]["edge_type"] == "IMPORTS_DECLARED"


def test_dependency_edges_query_filters_sources(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    try:
        payload_text = dependency_edges.render(
            snapshot_id,
            conn,
            repo_root,
            query="pkg.alpha",
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["edges"]
    assert all(edge["from_module_qualified_name"].startswith("pkg.alpha") for edge in payload["edges"])


def test_import_references_returns_importers(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    try:
        payload_text = import_references.render(
            snapshot_id,
            conn,
            repo_root,
            module_id="pkg.alpha",
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["edges"]
    assert any(edge["from_module_qualified_name"] == "pkg.beta" for edge in payload["edges"])


def test_importers_index_returns_importers(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    try:
        payload_text = importers_index.render(
            snapshot_id,
            conn,
            repo_root,
            module_id="pkg.alpha",
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["importers"]
    assert any(entry["module_qualified_name"] == "pkg.beta" for entry in payload["importers"])


def test_module_file_map_returns_modules(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    try:
        payload_text = module_file_map.render(
            snapshot_id,
            conn,
            repo_root,
            module_id="pkg.alpha",
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["modules"]
    assert payload["modules"][0]["module_qualified_name"].startswith("pkg.alpha")


def test_file_outline_returns_nodes(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    try:
        payload_text = file_outline.render(
            snapshot_id,
            conn,
            repo_root,
            module_id="pkg.alpha",
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["files"]
    assert any(entry["nodes"] for entry in payload["files"])


def test_concatenated_source_class_scope(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    try:
        payload_text = concatenated_source.render(
            snapshot_id,
            conn,
            repo_root,
            scope="class",
            class_id="pkg.alpha.Service",
        )
    finally:
        conn.close()
    assert "pkg/alpha/service.py" in payload_text


def test_callsite_index_reducer_returns_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    try:
        payload_text = callsite_index.render(
            snapshot_id,
            conn,
            repo_root,
            function_id="pkg.alpha.service.helper",
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["callable_id"]
    assert "edges" in payload
    assert "artifact_available" in payload
    assert "edge_source" in payload
    if payload["edges"]:
        edge = payload["edges"][0]
        assert "caller_node_type" in edge
        assert "callee_node_type" in edge


def test_callable_source_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    try:
        payload_text = callable_source.render(
            snapshot_id,
            conn,
            repo_root,
            function_id="pkg.alpha.service.helper",
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["file_path"]
    assert payload["source"]
