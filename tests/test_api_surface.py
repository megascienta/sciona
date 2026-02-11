# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from sciona import api
from sciona.runtime import paths as runtime_paths


def test_public_api_root_exposes_namespaces_only():
    assert api.__all__ == ["addons"]
    for name in api.__all__:
        assert hasattr(api, name)


def test_public_addon_api_surface_is_explicit_and_stable():
    expected = [
        "PLUGIN_API_VERSION",
        "PLUGIN_API_MAJOR",
        "PLUGIN_API_MINOR",
        "emit",
        "list_entries",
        "open_core_readonly",
        "open_artifact_readonly",
        "core_readonly",
        "artifact_readonly",
    ]
    assert api.addons.__all__ == expected
    assert len(api.addons.__all__) == len(set(api.addons.__all__))
    for name in expected:
        assert hasattr(api.addons, name), f"Missing addon API symbol: {name}"


def test_addon_api_can_list_reducers(repo_with_snapshot, monkeypatch):
    repo_root, _snapshot_id = repo_with_snapshot
    monkeypatch.setattr(runtime_paths, "get_repo_root", lambda: repo_root)
    entries = api.addons.list_entries()
    assert entries
    reducer_ids = {entry["reducer_id"] for entry in entries}
    assert "structural_index" in reducer_ids
