# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_CODE_ANALYSIS_ROOT = _REPO_ROOT / "src" / "sciona" / "code_analysis"


# Temporary migration exceptions removed in follow-up PRs.
_ALLOWLIST_AST_PARSE: set[str] = set()

_ALLOWLIST_LINE_BASED_FALLBACK: set[str] = set()


pytestmark = [pytest.mark.policy]


def _rel(path: Path) -> str:
    return path.relative_to(_CODE_ANALYSIS_ROOT).as_posix()


@lru_cache(maxsize=1)
def _python_file_texts() -> dict[str, str]:
    return {
        _rel(path): path.read_text(encoding="utf-8")
        for path in sorted(_CODE_ANALYSIS_ROOT.rglob("*.py"))
    }


def test_policy_no_tree_sitter_wrapper_module() -> None:
    assert not (_CODE_ANALYSIS_ROOT / "tools" / "tree_sitter.py").exists()


def test_policy_no_typescript_structural_regex_fallback() -> None:
    path = (
        _CODE_ANALYSIS_ROOT
        / "languages"
        / "builtin"
        / "typescript"
        / "typescript_node_walk.py"
    )
    text = path.read_text(encoding="utf-8")
    assert 're.search(r"\\bextends\\s+([A-Za-z0-9_\\.]+)",' not in text


def test_policy_profile_introspection_uses_bootstrap_helper() -> None:
    tools_root = _CODE_ANALYSIS_ROOT / "tools"
    paths = (
        tools_root / "profiling" / "python.py",
        tools_root / "profiling" / "typescript.py",
        tools_root / "profiling" / "java.py",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "bootstrap_tree_sitter_parser(" in text
        assert "Parser()" not in text
        assert "get_language(" not in text
        assert ".set_language(" not in text


def test_policy_only_narrow_parser_bootstrap_helper() -> None:
    violations: list[str] = []
    for rel, text in _python_file_texts().items():
        if "def build_parser(" in text:
            violations.append(f"{rel}: def build_parser(")
        if "build_parser =" in text:
            violations.append(f"{rel}: build_parser =")
        if "def parser_factory(" in text:
            violations.append(f"{rel}: def parser_factory(")
        if "def make_parser(" in text:
            violations.append(f"{rel}: def make_parser(")
        if (
            "def bootstrap_tree_sitter_parser(" in text
            and rel != "core/extract/parsing/parser_bootstrap.py"
        ):
            violations.append(f"{rel}: bootstrap_tree_sitter_parser outside canonical module")
    assert not violations


def test_policy_no_ast_parse_in_code_analysis() -> None:
    violations: list[str] = []
    for rel, text in _python_file_texts().items():
        if rel in _ALLOWLIST_AST_PARSE:
            continue
        if "ast.parse(" in text:
            violations.append(f"{rel}: ast.parse(")
        if "tools.tree_sitter" in text:
            violations.append(f"{rel}: tools.tree_sitter")
        if "from .tree_sitter import build_parser" in text:
            violations.append(f"{rel}: from .tree_sitter import build_parser")
    assert not violations


def test_policy_no_line_based_parameter_fallback() -> None:
    violations: list[str] = []
    for rel, text in _python_file_texts().items():
        if rel in _ALLOWLIST_LINE_BASED_FALLBACK:
            continue
        if "def _line_based_ts_parameters(" in text:
            violations.append(f"{rel}: def _line_based_ts_parameters(")
        if "_line_based_ts_parameters(" in text:
            violations.append(f"{rel}: _line_based_ts_parameters(")
        if "def _split_comma_aware(" in text:
            violations.append(f"{rel}: def _split_comma_aware(")
        if "_parse_typescript_parameters(" in text:
            violations.append(f"{rel}: _parse_typescript_parameters(")
        if "_parse_typescript_bases(" in text:
            violations.append(f"{rel}: _parse_typescript_bases(")
    assert not violations


def test_policy_structural_extraction_avoids_non_query_traversal() -> None:
    violations: list[str] = []
    for rel, text in _python_file_texts().items():
        if not rel.startswith("core/extract/"):
            continue
        if rel in {"core/extract/parser_bootstrap.py", "core/extract/query_helpers.py"}:
            if "stack = [node]" in text:
                violations.append(f"{rel}: stack = [node]")
            if "stack.pop()" in text:
                violations.append(f"{rel}: stack.pop()")
            continue
        if "find_nodes_of_type(" in text:
            violations.append(f"{rel}: find_nodes_of_type(")
    assert not violations


def test_policy_core_language_modules_are_not_implemented_in_core() -> None:
    shims_root = _CODE_ANALYSIS_ROOT / "core" / "extract" / "languages"
    for path in sorted(shims_root.glob("*.py")):
        assert path.name == "__init__.py"
