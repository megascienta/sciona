# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import json
import sqlite3

from sciona.reducers.baseline import callable_source, concatenated_source

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


def test_concatenated_source_codebase_scope(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = concatenated_source.render(
            snapshot_id,
            conn,
            repo_root,
            scope="codebase",
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    paths = {entry["path"] for entry in payload["files"]}
    assert "pkg/alpha/service.py" in paths
    assert "pkg/beta/__init__.py" in paths


def test_concatenated_source_module_scope(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = concatenated_source.render(
            snapshot_id,
            conn,
            repo_root,
            scope="module",
            module_id="pkg.alpha",
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    paths = {entry["path"] for entry in payload["files"]}
    assert "pkg/alpha/service.py" in paths
    assert "pkg/beta/__init__.py" not in paths


def test_concatenated_source_class_scope(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
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
    payload = json.loads(_strip_json_fence(payload_text))
    paths = {entry["path"] for entry in payload["files"]}
    assert "pkg/alpha/service.py" in paths


def test_callable_source_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
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
