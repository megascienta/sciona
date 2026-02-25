# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_CODE_ANALYSIS_ROOT = _REPO_ROOT / "src" / "sciona" / "code_analysis"


# Temporary migration exceptions removed in follow-up PRs.
_ALLOWLIST_AST_PARSE: set[str] = set()

_ALLOWLIST_LINE_BASED_FALLBACK: set[str] = set()


def _python_files() -> list[Path]:
    return sorted(_CODE_ANALYSIS_ROOT.rglob("*.py"))


def _rel(path: Path) -> str:
    return path.relative_to(_CODE_ANALYSIS_ROOT).as_posix()


def test_policy_no_tree_sitter_wrapper_module() -> None:
    assert not (_CODE_ANALYSIS_ROOT / "tools" / "tree_sitter.py").exists()


@pytest.mark.parametrize("path", _python_files(), ids=lambda p: _rel(p))
def test_policy_no_parser_factory_wrapper(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "def build_parser(" not in text
    assert "build_parser =" not in text


@pytest.mark.parametrize("path", _python_files(), ids=lambda p: _rel(p))
def test_policy_no_ast_parse_in_code_analysis(path: Path) -> None:
    rel = _rel(path)
    text = path.read_text(encoding="utf-8")
    if rel in _ALLOWLIST_AST_PARSE:
        return
    assert "ast.parse(" not in text
    assert "tools.tree_sitter" not in text
    assert "from .tree_sitter import build_parser" not in text


@pytest.mark.parametrize("path", _python_files(), ids=lambda p: _rel(p))
def test_policy_no_line_based_parameter_fallback(path: Path) -> None:
    rel = _rel(path)
    text = path.read_text(encoding="utf-8")
    if rel in _ALLOWLIST_LINE_BASED_FALLBACK:
        return
    assert "def _line_based_ts_parameters(" not in text
    assert "_line_based_ts_parameters(" not in text
    assert "def _split_comma_aware(" not in text
    assert "_parse_typescript_parameters(" not in text
    assert "_parse_typescript_bases(" not in text


@pytest.mark.parametrize("path", _python_files(), ids=lambda p: _rel(p))
def test_policy_structural_extraction_avoids_non_query_traversal(path: Path) -> None:
    rel = _rel(path)
    if not rel.startswith("core/extract/"):
        return
    text = path.read_text(encoding="utf-8")
    if rel == "core/extract/utils.py":
        assert "stack = [node]" not in text
        assert "stack.pop()" not in text
        return
    assert "find_nodes_of_type(" not in text
