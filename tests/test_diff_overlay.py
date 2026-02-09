# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json

from sciona import api


def _parse_json_payload(text: str) -> dict:
    stripped = text.strip()
    assert stripped.startswith("```json")
    body = stripped.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(body)


def test_dirty_overlay_adds_node(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return 1\n\n\ndef helper2():\n    return 2\n",
        encoding="utf-8",
    )

    text, _, _ = api.reducers.emit(
        "module_overview",
        repo_root=repo_root,
        module_id="pkg.alpha",
    )
    payload = _parse_json_payload(text)
    diff = payload.get("_diff")
    assert diff, "Expected diff overlay in reducer payload"
    assert diff["version"] == 2
    assert diff["mode"] == "full"
    assert diff["overlay_available"] is True
    assert diff["worktree_hash"]
    assert diff.get("patched", {}).get("projection") is True
    assert "coverage" in diff
    adds = diff["changes"]["nodes"]["add"]
    assert any("helper2" in (entry.get("new_value") or "") for entry in adds)


def test_dirty_overlay_calls_and_summary(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return 1\n\n\ndef caller():\n    return helper()\n",
        encoding="utf-8",
    )

    text, _, _ = api.reducers.emit(
        "fan_summary",
        repo_root=repo_root,
    )
    payload = _parse_json_payload(text)
    diff = payload.get("_diff")
    assert diff, "Expected diff overlay in reducer payload"
    assert diff.get("coverage", {}).get("summary") in {"partial", "none"}
    assert diff.get("changes", {}).get("calls", {}).get("add"), "Expected call edge diffs"
    summary = diff.get("summary")
    assert summary, "Expected diff summary"
    assert summary["calls"]["add"] >= 1
