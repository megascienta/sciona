# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json

from sciona import api
from sciona.runtime import paths as runtime_paths


def _parse_json_payload(text: str) -> dict:
    stripped = text.strip()
    assert stripped.startswith("```json")
    body = stripped.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(body)


def _q(repo_root, name: str) -> str:
    return f"{runtime_paths.repo_name_prefix(repo_root)}.{name}"


def test_dirty_overlay_adds_node(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return 1\n\n\ndef helper2():\n    return 2\n",
        encoding="utf-8",
    )

    text, _, _ = api.addons.emit(
        "module_overview",
        repo_root=repo_root,
        module_id=_q(repo_root, "pkg.alpha"),
    )
    payload = _parse_json_payload(text)
    diff = payload.get("_diff")
    assert diff, "Expected diff overlay in reducer payload"
    assert diff["version"] == 3
    assert diff["overlay_available"] is True
    assert diff["worktree_hash"]
    assert diff.get("affected") is True
    assert "nodes" in diff.get("affected_by", [])


def test_dirty_overlay_calls_and_summary(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return 1\n\n\ndef caller():\n    return helper()\n",
        encoding="utf-8",
    )

    text, _, _ = api.addons.emit(
        "fan_summary",
        repo_root=repo_root,
    )
    payload = _parse_json_payload(text)
    diff = payload.get("_diff")
    assert diff, "Expected diff overlay in reducer payload"
    assert diff.get("affected") is True
    assert "calls" in diff.get("affected_by", [])


def test_dirty_overlay_summary_mode(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return 1\n\n\ndef helper3():\n    return 3\n",
        encoding="utf-8",
    )

    text, _, _ = api.addons.emit(
        "module_overview",
        repo_root=repo_root,
        module_id=_q(repo_root, "pkg.alpha"),
        diff_mode="summary",
    )
    payload = _parse_json_payload(text)
    diff = payload.get("_diff")
    assert diff, "Expected diff overlay in reducer payload"
    assert diff["overlay_available"] is True
    assert diff["worktree_hash"]
    assert diff.get("affected") is True
    assert "nodes" in diff.get("affected_by", [])


def test_dirty_overlay_fan_summary_node_id_updates(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return 1\n\n\ndef caller():\n    return helper()\n",
        encoding="utf-8",
    )

    text, _, _ = api.addons.emit(
        "fan_summary",
        repo_root=repo_root,
        function_id=_q(repo_root, "pkg.alpha.service.helper"),
    )
    payload = _parse_json_payload(text)
    edge_kinds = payload.get("edge_kinds") or {}
    calls = edge_kinds.get("CALLS") or {}
    assert calls.get("fan_in") == 1


def test_dirty_overlay_hotspot_summary_size_updates(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    text, _, _ = api.addons.emit(
        "hotspot_summary",
        repo_root=repo_root,
    )
    payload = _parse_json_payload(text)
    baseline = {
        entry.get("module_qualified_name"): entry.get("count")
        for entry in payload.get("by_size", [])
    }

    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return 1\n\n\ndef helper2():\n    return 2\n",
        encoding="utf-8",
    )

    text, _, _ = api.addons.emit(
        "hotspot_summary",
        repo_root=repo_root,
    )
    payload = _parse_json_payload(text)
    updated = {
        entry.get("module_qualified_name"): entry.get("count")
        for entry in payload.get("by_size", [])
    }
    prefix = runtime_paths.repo_name_prefix(repo_root)
    baseline_count = baseline.get(f"{prefix}.pkg.alpha") or 0
    assert updated.get(f"{prefix}.pkg.alpha") == baseline_count - 1
