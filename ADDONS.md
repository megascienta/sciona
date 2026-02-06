# SCIONA Addons Guide

This document is self-contained for addon developers. It is intended to live
in addons repositories.
For user-facing expectations and the public contract, see `USERGUIDE.md` in
the core repo.

## What addons can do

Addons can register additional CLI commands under their own namespace.
Addons must not register reducers (core-owned for determinism and DB lifecycle
ownership).

## Entry point

Addons are discovered via Python entry points:
- Entry point group: `sciona.addons`
- Each entry point must be a callable that accepts a `Registry`.

Example (pyproject.toml):
```toml
[project.entry-points."sciona.addons"]
my_addon = "my_addon.plugin:register"
```

Example (plugin.py):
```python
from sciona.runtime.addon_api import Registry

REQUIRES_SCIONA_PLUGIN_API = ">=1,<2"


def register(registry: Registry) -> None:
    registry.register_cli("my-addon", build_cli_app())
```

## Registry API

The addon registry supports:
- `register_cli(name, app)` to register a Typer-compatible CLI app.

Reducers are core-owned and cannot be registered by addons.

## Compatibility contract

Addons declare the plugin API version via:
- `REQUIRES_SCIONA_PLUGIN_API` (module or function attribute)

Supported formats:
- integer major (e.g., `1`)
- string major or major.minor (e.g., `"1"`, `"1.0"`)
- range string (e.g., `">=1,<2"`)

Versioning policy:
- Major bump: breaking changes to Registry API.
- Minor bump: additive, backward-compatible changes.

If incompatible, the addon is skipped with a warning.

## Disable addons

Set environment flags to disable addon loading:
- `SCIONA_DISABLE_ADDONS=1`
- `SCIONA_SAFE_MODE=1`

## Hello addon (minimal walkthrough)

1. Install your addon package into the environment.
2. Run `sciona --help` and confirm your namespace appears.
3. Run your addon command via `sciona <your-namespace> ...`.

## Packaging and testing

- Package as a standard Python project with entry points.
- Test CLI integration by invoking `sciona` with your addon installed.

## Limitations

- Addons do not modify SCIONA core snapshots or reducers.
- Addons should not rely on private/internal APIs.

For core behavior, see `README.md` and `USERGUIDE.md` in the core repo.
