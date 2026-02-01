from __future__ import annotations

from sciona import api


def test_public_api_surface_is_explicit_and_stable():
    expected = [
        "run",
        "register_cli_commands",
        "init",
        "build",
        "rebuild",
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
        "Registry",
        "load",
        "load_for_cli",
        "run_build_hooks",
        "run_inits",
        "apply_app_hooks",
        "apply_prompts_and_reducers",
        "is_enabled",
        "core",
        "artifact",
        "runtime",
        "reducers",
    ]

    assert api.__all__ == expected
    assert len(api.__all__) == len(set(api.__all__))
    for name in expected:
        assert hasattr(api, name), f"Missing public API symbol: {name}"
