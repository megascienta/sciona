from __future__ import annotations

from sciona import api


def test_public_api_root_exposes_namespaces_only():
    assert api.__all__ == ["user", "plugins"]
    assert hasattr(api, "user")
    assert hasattr(api, "plugins")


def test_public_user_api_surface_is_explicit_and_stable():
    expected = [
        "run",
        "register_cli_commands",
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


def test_public_plugin_api_surface_is_explicit_and_stable():
    expected = [
        "PLUGIN_API_VERSION",
        "PLUGIN_API_MAJOR",
        "PLUGIN_API_MINOR",
        "Registry",
        "compile_prompt_payload",
        "emit",
    ]
    assert api.plugins.__all__ == expected
    assert len(api.plugins.__all__) == len(set(api.plugins.__all__))
    for name in expected:
        assert hasattr(api.plugins, name), f"Missing plugin API symbol: {name}"
