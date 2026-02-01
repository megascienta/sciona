from __future__ import annotations

from pathlib import Path

import yaml

from sciona.runtime import addons as addon_runtime


class _EntryPoints:
    def __init__(self, entries):
        self._entries = entries

    def select(self, *, group: str):
        if group == "sciona.addons":
            return list(self._entries)
        return []


class _Entry:
    def __init__(self, name, loader):
        self.name = name
        self._loader = loader

    def load(self):
        return self._loader


def test_discover_installed_addons_uses_entry_points(monkeypatch):
    entry = _Entry("documentation", lambda _registry: None)
    monkeypatch.setattr(
        addon_runtime.metadata,
        "entry_points",
        lambda: _EntryPoints([entry]),
    )

    installed = addon_runtime._discover_installed_addons()

    assert list(installed.keys()) == ["documentation"]


def test_load_respects_enabled_list(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    config_path = addon_runtime.runtime_paths.get_config_path(repo_root)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.safe_dump({"addons": ["alpha"]}, sort_keys=False),
        encoding="utf-8",
    )

    def _register(registry):
        registry.register_cli("alpha", object())

    installed = {
        "alpha": _Entry("alpha", _register),
        "beta": _Entry("beta", lambda _registry: None),
    }
    monkeypatch.setattr(addon_runtime, "_discover_installed_addons", lambda: installed)
    monkeypatch.setattr(addon_runtime, "_addons_disabled", lambda: False)

    registry = addon_runtime.load(repo_root)

    assert "alpha" in registry.cli_apps
    assert "beta" not in registry.cli_apps


def test_load_enabled_addon_list_wildcard(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    config_path = addon_runtime.runtime_paths.get_config_path(repo_root)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.safe_dump({"addons": ["*"]}, sort_keys=False),
        encoding="utf-8",
    )

    enabled = addon_runtime._load_enabled_addon_list(repo_root, ["b", "a"])

    assert enabled == ["a", "b"]


def test_apply_app_hooks_calls_hooks():
    registry = addon_runtime.Registry()
    calls = []

    def _hook(app):
        calls.append(app)

    registry.register_app_hook(_hook)

    app = object()
    addon_runtime.apply_app_hooks(registry, app)

    assert calls == [app]
