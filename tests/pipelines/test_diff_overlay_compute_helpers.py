# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from pathlib import Path

from sciona.code_analysis.core.normalize_model import FileRecord, FileSnapshot, SemanticNodeRecord
from sciona.pipelines.diff_overlay.compute import config as compute_config
from sciona.pipelines.diff_overlay.compute.payloads import node_content_hash
from sciona.pipelines.diff_overlay.compute.summary import summarize_overlay
from sciona.runtime.errors import ConfigError


def test_resolve_enabled_languages_returns_only_enabled(monkeypatch, tmp_path) -> None:
    class _Cfg:
        def __init__(self, enabled: bool):
            self.enabled = enabled

    monkeypatch.setattr(
        compute_config.runtime_config,
        "load_language_settings",
        lambda repo_root: {
            "python": _Cfg(True),
            "java": _Cfg(False),
            "typescript": _Cfg(True),
        },
    )

    assert compute_config.resolve_enabled_languages(tmp_path) == ["python", "typescript"]


def test_resolve_enabled_languages_falls_back_on_config_error(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        compute_config.runtime_config,
        "load_language_settings",
        lambda repo_root: (_ for _ in ()).throw(ConfigError("bad config")),
    )

    assert compute_config.resolve_enabled_languages(tmp_path) == sorted(
        compute_config.analysis_config.LANGUAGE_CONFIG.keys()
    )


def test_node_content_hash_uses_canonical_span_when_bytes_available(tmp_path) -> None:
    content = b"def helper():\r\n    return 1\r\n"
    snapshot = FileSnapshot(
        record=FileRecord(
            path=tmp_path / "mod.py",
            relative_path=Path("pkg/mod.py"),
            language="python",
        ),
        file_id="file",
        blob_sha="blob-sha",
        size=len(content),
        line_count=2,
        content=content,
    )
    node = SemanticNodeRecord(
        language="python",
        node_type="callable",
        qualified_name="pkg.mod.helper",
        display_name="helper",
        file_path=Path("pkg/mod.py"),
        start_line=1,
        end_line=2,
        start_byte=0,
        end_byte=len(content),
    )

    hashed = node_content_hash(node, snapshot)

    assert hashed != "blob-sha"


def test_node_content_hash_falls_back_to_blob_sha_without_valid_span(tmp_path) -> None:
    content = b"def helper():\n    return 1\n"
    snapshot = FileSnapshot(
        record=FileRecord(
            path=tmp_path / "mod.py",
            relative_path=Path("pkg/mod.py"),
            language="python",
        ),
        file_id="file",
        blob_sha="blob-sha",
        size=len(content),
        line_count=2,
        content=content,
    )
    node = SemanticNodeRecord(
        language="python",
        node_type="callable",
        qualified_name="pkg.mod.helper",
        display_name="helper",
        file_path=Path("pkg/mod.py"),
        start_line=1,
        end_line=2,
        start_byte=None,
        end_byte=None,
    )

    assert node_content_hash(node, snapshot) == "blob-sha"


def test_summarize_overlay_counts_nodes_edges_and_calls() -> None:
    rows = [
        {"node_type": "callable", "diff_kind": "add"},
        {"node_type": "callable", "diff_kind": "modify"},
        {
            "node_type": "edge",
            "diff_kind": "add",
            "new_value": '{"edge_type":"IMPORTS_DECLARED"}',
        },
        {
            "node_type": "edge",
            "diff_kind": "remove",
            "old_value": '{"edge_type":"LEXICALLY_CONTAINS"}',
        },
    ]
    call_rows = [
        {"diff_kind": "add"},
        {"diff_kind": "remove"},
    ]

    summary = summarize_overlay(rows, call_rows)

    assert summary == {
        "nodes": {
            "total": {"add": 1, "modify": 1, "remove": 0},
            "by_type": {"callable": {"add": 1, "modify": 1, "remove": 0}},
        },
        "edges": {
            "total": {"add": 1, "remove": 1},
            "by_type": {
                "IMPORTS_DECLARED": {"add": 1, "remove": 0},
                "LEXICALLY_CONTAINS": {"add": 0, "remove": 1},
            },
        },
        "calls": {"add": 1, "remove": 1},
    }


def test_summarize_overlay_returns_none_for_empty_changes() -> None:
    assert summarize_overlay([], []) is None
