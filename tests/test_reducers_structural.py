# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import json
import sqlite3

from sciona.reducers.core import (
    dependency_edges,
    file_outline,
    symbol_lookup,
    symbol_references,
)

from tests.helpers import seed_repo_with_snapshot


def _strip_json_fence(text: str) -> str:
    trimmed = text.strip()
    if trimmed.startswith("```json") and trimmed.endswith("```"):
        lines = trimmed.splitlines()
        return "\n".join(lines[1:-1])
    return trimmed


def _core_conn(repo_root):
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    return conn


def test_symbol_lookup_reducer_returns_matches(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
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
    conn = _core_conn(repo_root)
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


def test_symbol_lookup_deterministic_prelimit_with_duplicate_names(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    duplicate_name = "pkg.duplicate.target"
    duplicate_paths = [
        "pkg/z_last.py",
        "pkg/y_last.py",
        "pkg/x_last.py",
        "pkg/w_last.py",
        "pkg/v_last.py",
        "pkg/a_first.py",
    ]
    try:
        for idx, file_path in enumerate(duplicate_paths):
            structural_id = f"dup_{idx}"
            conn.execute(
                """
                INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
                VALUES (?, ?, ?, ?)
                """,
                (structural_id, "function", "python", snapshot_id),
            )
            conn.execute(
                """
                INSERT INTO node_instances(
                    instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{snapshot_id}:{structural_id}",
                    structural_id,
                    snapshot_id,
                    duplicate_name,
                    file_path,
                    1,
                    10,
                    f"hash-{structural_id}",
                ),
            )
        conn.commit()
        payload_text = symbol_lookup.render(
            snapshot_id,
            conn,
            repo_root,
            query="pkg.duplicate.target",
            kind="function",
            limit=1,
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["matches"]
    assert payload["matches"][0]["qualified_name"] == duplicate_name
    assert payload["matches"][0]["file_path"] == "pkg/a_first.py"


def test_symbol_references_returns_relationships(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
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
    conn = _core_conn(repo_root)
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
    conn = _core_conn(repo_root)
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
    conn = _core_conn(repo_root)
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
    assert all(
        edge["from_module_qualified_name"].startswith("pkg.alpha")
        for edge in payload["edges"]
    )


def test_file_outline_returns_nodes(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
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


def test_dependency_edges_direction_filters(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = dependency_edges.render(
            snapshot_id,
            conn,
            repo_root,
            module_id="pkg.alpha",
            direction="out",
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["edges"]
    assert all(
        edge["from_module_qualified_name"].startswith("pkg.alpha")
        for edge in payload["edges"]
    )
    conn = _core_conn(repo_root)
    try:
        payload_text = dependency_edges.render(
            snapshot_id,
            conn,
            repo_root,
            module_id="pkg.alpha",
            direction="in",
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["edges"]
    assert all(
        edge["to_module_qualified_name"].startswith("pkg.alpha")
        for edge in payload["edges"]
    )
