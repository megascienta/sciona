from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


FORBIDDEN_IMPORTS = {
    "runtime": {"reducers", "pipelines", "cli"},
    "data_storage": {"code_analysis", "pipelines", "cli"},
    "code_analysis": {"cli", "typer"},
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


def _scan_forbidden(top_package: str) -> list[str]:
    violations: list[str] = []
    forbidden = FORBIDDEN_IMPORTS[top_package]
    package_root = ROOT / top_package
    for path in package_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(ROOT)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name.split(".")[0]
                    if target in forbidden:
                        violations.append(f"{rel}:{node.lineno} imports {alias.name!r}")
            elif isinstance(node, ast.ImportFrom):
                target = _module_from_importfrom(path, node)
                if target in forbidden:
                    module = node.module or ""
                    violations.append(f"{rel}:{node.lineno} imports from {module!r}")
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
