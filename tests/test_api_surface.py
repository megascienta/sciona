from __future__ import annotations

from sciona import api
from sciona.runtime import paths as runtime_paths


def test_public_api_root_exposes_namespaces_only():
    assert api.__all__ == [
        "user",
        "addons",
        "prompts",
        "reducers",
        "repo",
        "resolve",
        "runtime",
        "errors",
    ]
    for name in api.__all__:
        assert hasattr(api, name)


def test_public_user_api_surface_is_explicit_and_stable():
    expected = [
        "init",
        "build",
        "status",
        "init_dialog_defaults",
        "init_supported_languages",
        "init_apply_languages",
        "clean",
        "clean_agents",
        "emit",
        "list_entries",
        "get_entry",
        "identifier_for_repo",
        "identifier",
        "require_identifier",
    ]

    assert api.user.__all__ == expected
    assert len(api.user.__all__) == len(set(api.user.__all__))
    for name in expected:
        assert hasattr(api.user, name), f"Missing user API symbol: {name}"


def test_public_addon_api_surface_is_explicit_and_stable():
    expected = [
        "PLUGIN_API_VERSION",
        "PLUGIN_API_MAJOR",
        "PLUGIN_API_MINOR",
        "Registry",
        "load_for_cli",
        "compile_prompt_payload",
        "emit",
        "list_entries",
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
