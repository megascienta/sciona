# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import ast
from pathlib import Path

import pytest


ALLOWED_MODULES = {
    "sciona.api.addons",
}
ALLOWED_PREFIXES = ("sciona.addons",)
pytestmark = [pytest.mark.policy]


def _is_allowed_import_name(name: str) -> bool:
    if name in ALLOWED_MODULES:
        return True
    if any(
        name == prefix or name.startswith(f"{prefix}.") for prefix in ALLOWED_PREFIXES
    ):
        return True
    return False


def _is_allowed_import_from(module: str, names: list[str]) -> bool:
    if module in ALLOWED_MODULES:
        return True
    if any(
        module == prefix or module.startswith(f"{prefix}.")
        for prefix in ALLOWED_PREFIXES
    ):
        return True
    return False


def test_addons_import_core_via_public_api_only():
    violations: list[str] = []
    addons_root = Path("addons")
    for path in addons_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("sciona") and not _is_allowed_import_name(
                        alias.name
                    ):
                        violations.append(
                            f"{path}:{node.lineno} disallowed import {alias.name!r}"
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module
                if module and module.startswith("sciona"):
                    names = [alias.name for alias in node.names]
                    if not _is_allowed_import_from(module, names):
                        violations.append(
                            f"{path}:{node.lineno} disallowed from {module!r} "
                            f"import {', '.join(names)}"
                        )

    assert not violations, "Addon import boundary violations:\n" + "\n".join(violations)
