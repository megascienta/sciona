from __future__ import annotations

from pathlib import Path

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


def test_load_registers_all_installed(monkeypatch):
    def _register_alpha(registry):
        registry.register_cli("alpha", object())

    def _register_beta(registry):
        registry.register_cli("beta", object())

    installed = {
        "alpha": _Entry("alpha", _register_alpha),
        "beta": _Entry("beta", _register_beta),
    }
    monkeypatch.setattr(addon_runtime, "_discover_installed_addons", lambda: installed)
    monkeypatch.setattr(addon_runtime, "_addons_disabled", lambda: False)

    registry = addon_runtime.load(Path("."))

    assert "alpha" in registry.cli_apps
    assert "beta" in registry.cli_apps


def test_load_enabled_addon_list_returns_sorted():
    enabled = addon_runtime._load_enabled_addon_list(["b", "a"])

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
