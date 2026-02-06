# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.runtime import addons as addon_runtime


def test_load_skips_import_errors(monkeypatch):
    monkeypatch.setattr(addon_runtime, "_addons_disabled", lambda: False)

    def _boom(_registry):
        raise RuntimeError("import exploded")

    class _Entry:
        def load(self):
            return _boom

    monkeypatch.setattr(
        addon_runtime, "_discover_installed_addons", lambda: {"broken": _Entry()}
    )

    registry = addon_runtime.load(repo_root=None)
    assert not registry.cli_apps


def test_load_skips_register_errors(monkeypatch):
    monkeypatch.setattr(addon_runtime, "_addons_disabled", lambda: False)

    def _register(_registry):
        raise RuntimeError("register exploded")

    class _Entry:
        def load(self):
            return _register

    monkeypatch.setattr(
        addon_runtime, "_discover_installed_addons", lambda: {"bad": _Entry()}
    )

    registry = addon_runtime.load(repo_root=None)
    assert not registry.cli_apps
