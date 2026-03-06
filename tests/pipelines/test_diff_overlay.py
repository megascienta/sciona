# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from sciona import api
from tests.helpers import parse_json_payload, qualify_repo_name


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
        module_id=qualify_repo_name(repo_root, "pkg.alpha"),
    )
    payload = parse_json_payload(text)
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
    payload = parse_json_payload(text)
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
        module_id=qualify_repo_name(repo_root, "pkg.alpha"),
        diff_mode="summary",
    )
    payload = parse_json_payload(text)
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
        callable_id=qualify_repo_name(repo_root, "pkg.alpha.service.helper"),
    )
    payload = parse_json_payload(text)
    edge_kinds = payload.get("edge_kinds") or {}
    calls = edge_kinds.get("CALLS") or {}
    assert calls.get("fan_in") == 1


def test_dirty_overlay_hotspot_summary_size_updates(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    text, _, _ = api.addons.emit(
        "hotspot_summary",
        repo_root=repo_root,
    )
    payload = parse_json_payload(text)
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
    payload = parse_json_payload(text)
    updated = {
        entry.get("module_qualified_name"): entry.get("count")
        for entry in payload.get("by_size", [])
    }
    module_id = qualify_repo_name(repo_root, "pkg.alpha")
    baseline_count = baseline.get(module_id) or 0
    assert updated.get(module_id) == baseline_count - 1


def test_non_indexed_dirty_does_not_attach_overlay_warning(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    (repo_root / "README.md").write_text("dirty docs\n", encoding="utf-8")

    text, _, _ = api.addons.emit(
        "module_overview",
        repo_root=repo_root,
        module_id=qualify_repo_name(repo_root, "pkg.alpha"),
    )
    payload = parse_json_payload(text)
    assert payload.get("_diff") is None
    assert payload.get("snapshot_warning") is None


def test_out_of_scope_indexed_dirty_marks_diff_not_affected(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    (repo_root / "pkg/beta/__init__.py").write_text("x = 1\n", encoding="utf-8")

    text, _, _ = api.addons.emit(
        "module_overview",
        repo_root=repo_root,
        module_id=qualify_repo_name(repo_root, "pkg.alpha"),
    )
    payload = parse_json_payload(text)
    diff = payload.get("_diff")
    assert diff, "Expected diff overlay in reducer payload"
    assert diff["overlay_available"] is True
    assert diff.get("affected") is False


def test_dirty_overlay_snapshot_provenance_marks_projection_not_supported(
    repo_with_snapshot,
):
    repo_root, _snapshot_id = repo_with_snapshot
    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return 1\n\n\ndef helper2():\n    return 2\n",
        encoding="utf-8",
    )

    text, _, _ = api.addons.emit(
        "snapshot_provenance",
        repo_root=repo_root,
    )
    payload = parse_json_payload(text)
    diff = payload.get("_diff")
    assert diff, "Expected diff overlay in reducer payload"
    assert diff["overlay_available"] is True
    assert diff.get("affected") is None
    warnings = diff.get("warnings") or []
    assert "projection_not_supported" in warnings
    assert "projection_not_patched" not in warnings
    warning = payload.get("snapshot_warning") or {}
    assert warning.get("code") == "DIRTY_OVERLAY_METADATA_ONLY"
    assert "committed-snapshot only" in str(warning.get("message") or "")
