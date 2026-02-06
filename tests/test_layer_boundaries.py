# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


FORBIDDEN_IMPORTS = {
    "runtime": {"reducers", "pipelines", "cli"},
    "data_storage": {"code_analysis", "pipelines", "cli"},
    "code_analysis": {"cli", "typer"},
    "pipelines": {"cli", "api"},
    "reducers": {"cli", "api", "pipelines"},
    "api": {"cli"},
    "cli": {"pipelines"},
}

RESPONSIBILITY_FORBIDDEN_IMPORTS = {
    "pipelines": {"runtime.config.parse"},
    "api": {"pipelines.domain"},
}


def _module_from_importfrom(path: Path, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return (node.module or "").split(".")[0] or None

    parts = list(path.relative_to(ROOT).parts[:-1])
    for _ in range(node.level):
        if parts:
            parts.pop()
    if node.module:
        parts.extend(node.module.split("."))
    return parts[0] if parts else None


def _resolve_importfrom_module(path: Path, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module
    parts = list(path.relative_to(ROOT).with_suffix("").parts[:-1])
    for _ in range(node.level):
        if parts:
            parts.pop()
    if node.module:
        parts.extend(node.module.split("."))
    return ".".join(parts) if parts else None


def _iter_imports(path: Path) -> list[tuple[str, int]]:
    imports: list[tuple[str, int]] = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            module = _resolve_importfrom_module(path, node)
            if module:
                imports.append((module, node.lineno))
    return imports


def _scan_forbidden(top_package: str) -> list[str]:
    violations: list[str] = []
    forbidden = FORBIDDEN_IMPORTS[top_package]
    package_root = ROOT / top_package
    for path in package_root.rglob("*.py"):
        rel = path.relative_to(ROOT)
        for module, lineno in _iter_imports(path):
            target = module.split(".")[0]
            if target in forbidden:
                violations.append(f"{rel}:{lineno} imports {module!r}")
    return violations


def _scan_responsibility(top_package: str) -> list[str]:
    violations: list[str] = []
    forbidden = RESPONSIBILITY_FORBIDDEN_IMPORTS[top_package]
    package_root = ROOT / top_package
    for path in package_root.rglob("*.py"):
        rel = path.relative_to(ROOT)
        for module, lineno in _iter_imports(path):
            for banned in forbidden:
                if module == banned or module.startswith(f"{banned}."):
                    violations.append(f"{rel}:{lineno} imports {module!r}")
    return violations


def test_runtime_import_boundaries() -> None:
    violations = _scan_forbidden("runtime")
    assert not violations, "Runtime boundary violations:\n" + "\n".join(violations)


def test_data_storage_import_boundaries() -> None:
    violations = _scan_forbidden("data_storage")
    assert not violations, "Storage boundary violations:\n" + "\n".join(violations)


def test_code_analysis_import_boundaries() -> None:
    violations = _scan_forbidden("code_analysis")
    assert not violations, "Analysis boundary violations:\n" + "\n".join(violations)


def test_pipelines_import_boundaries() -> None:
    violations = _scan_forbidden("pipelines")
    assert not violations, "Pipelines boundary violations:\n" + "\n".join(violations)


def test_reducers_import_boundaries() -> None:
    violations = _scan_forbidden("reducers")
    assert not violations, "Reducers boundary violations:\n" + "\n".join(violations)


def test_api_import_boundaries() -> None:
    violations = _scan_forbidden("api")
    assert not violations, "API boundary violations:\n" + "\n".join(violations)


def test_cli_import_boundaries() -> None:
    violations = _scan_forbidden("cli")
    assert not violations, "CLI boundary violations:\n" + "\n".join(violations)


def test_pipelines_responsibility_boundaries() -> None:
    violations = _scan_responsibility("pipelines")
    assert (
        not violations
    ), "Pipelines responsibility violations:\n" + "\n".join(violations)


def test_api_responsibility_boundaries() -> None:
    violations = _scan_responsibility("api")
    assert not violations, "API responsibility violations:\n" + "\n".join(violations)
