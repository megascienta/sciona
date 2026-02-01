from sciona.runtime import addons as addon_runtime


def test_load_skips_import_errors(monkeypatch):
    monkeypatch.setattr(addon_runtime, "_addons_disabled", lambda: False)
    monkeypatch.setattr(addon_runtime, "_load_enabled_addon_list", lambda _installed: ["broken"])

    def _boom(_registry):
        raise RuntimeError("import exploded")

    class _Entry:
        def load(self):
            return _boom

    monkeypatch.setattr(addon_runtime, "_discover_installed_addons", lambda: {"broken": _Entry()})

    registry = addon_runtime.load(repo_root=None)
    assert not registry.cli_apps
    assert not registry.init_hooks
    assert not registry.app_hooks


def test_load_skips_register_errors(monkeypatch):
    monkeypatch.setattr(addon_runtime, "_addons_disabled", lambda: False)

    def _register(_registry):
        raise RuntimeError("register exploded")

    class _Entry:
        def load(self):
            return _register

    monkeypatch.setattr(addon_runtime, "_discover_installed_addons", lambda: {"bad": _Entry()})
    monkeypatch.setattr(addon_runtime, "_load_enabled_addon_list", lambda _installed: ["bad"])

    registry = addon_runtime.load(repo_root=None)
    assert not registry.cli_apps
    assert not registry.init_hooks
    assert not registry.app_hooks
