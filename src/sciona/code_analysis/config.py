# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Centralized configuration for language handling and shared constants."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .core.extract.analyzer import ASTAnalyzer
    from .core.normalize.model import FileSnapshot

AnalyzerFactory = Callable[[], "ASTAnalyzer"]
ModuleNamer = Callable[[Path, "FileSnapshot"], str]


@dataclass(frozen=True)
class LanguageConfig:
    extensions: Tuple[str, ...]
    callable_types: Tuple[str, ...]
    analyzer_factory: Optional[AnalyzerFactory]
    module_namer: Optional[ModuleNamer]


def _python_analyzer_factory() -> "ASTAnalyzer":
    from .languages.builtin import python as python_lang

    return python_lang.PythonAnalyzer()


def _typescript_analyzer_factory() -> "ASTAnalyzer":
    from .languages.builtin import typescript as typescript_lang

    return typescript_lang.TypeScriptAnalyzer()


def _java_analyzer_factory() -> "ASTAnalyzer":
    from .languages.builtin import java as java_lang

    return java_lang.JavaAnalyzer()


def _javascript_analyzer_factory() -> "ASTAnalyzer":
    from .languages.builtin import javascript as javascript_lang

    return javascript_lang.JavaScriptAnalyzer()


def _python_module_namer(repo_root: Path, snapshot: "FileSnapshot") -> str:
    from .languages.builtin import python as python_lang

    return python_lang.module_name(repo_root, snapshot)


def _typescript_module_namer(repo_root: Path, snapshot: "FileSnapshot") -> str:
    from .languages.builtin import typescript as typescript_lang

    return typescript_lang.module_name(repo_root, snapshot)


def _java_module_namer(repo_root: Path, snapshot: "FileSnapshot") -> str:
    from .languages.builtin import java as java_lang

    return java_lang.module_name(repo_root, snapshot)


def _javascript_module_namer(repo_root: Path, snapshot: "FileSnapshot") -> str:
    from .languages.builtin import javascript as javascript_lang

    return javascript_lang.module_name(repo_root, snapshot)


CALLABLE_NODE_TYPES = frozenset({"callable"})
TERMINAL_IDENTIFIER_TYPES_BY_LANGUAGE = {
    "python": frozenset({"identifier"}),
    "typescript": frozenset(
        {
            "identifier",
            "property_identifier",
            "shorthand_property_identifier",
            "type_identifier",
        }
    ),
    "java": frozenset({"identifier", "type_identifier"}),
    "javascript": frozenset({"identifier", "property_identifier"}),
}

LANGUAGE_CONFIG: dict[str, LanguageConfig] = {
    "python": LanguageConfig(
        extensions=(".py",),
        callable_types=("callable",),
        analyzer_factory=_python_analyzer_factory,
        module_namer=_python_module_namer,
    ),
    "typescript": LanguageConfig(
        extensions=(".ts", ".tsx"),
        callable_types=("callable",),
        analyzer_factory=_typescript_analyzer_factory,
        module_namer=_typescript_module_namer,
    ),
    "java": LanguageConfig(
        extensions=(".java",),
        callable_types=("callable",),
        analyzer_factory=_java_analyzer_factory,
        module_namer=_java_module_namer,
    ),
    "javascript": LanguageConfig(
        extensions=(".js", ".mjs", ".cjs"),
        callable_types=("callable",),
        analyzer_factory=_javascript_analyzer_factory,
        module_namer=_javascript_module_namer,
    ),
}
