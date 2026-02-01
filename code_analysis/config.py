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
    from .core.extract.languages import python as python_lang

    return python_lang.PythonAnalyzer()


def _typescript_analyzer_factory() -> "ASTAnalyzer":
    from .core.extract.languages import typescript as typescript_lang

    return typescript_lang.TypeScriptAnalyzer()


def _java_analyzer_factory() -> "ASTAnalyzer":
    from .core.extract.languages import java as java_lang

    return java_lang.JavaAnalyzer()

def _python_module_namer(repo_root: Path, snapshot: "FileSnapshot") -> str:
    from .core.extract.languages import python as python_lang

    return python_lang.module_name(repo_root, snapshot)


def _typescript_module_namer(repo_root: Path, snapshot: "FileSnapshot") -> str:
    from .core.extract.languages import typescript as typescript_lang

    return typescript_lang.module_name(repo_root, snapshot)


def _java_module_namer(repo_root: Path, snapshot: "FileSnapshot") -> str:
    from .core.extract.languages import java as java_lang

    return java_lang.module_name(repo_root, snapshot)

CALLABLE_NODE_TYPES = frozenset({"function", "method"})
TERMINAL_IDENTIFIER_TYPES = frozenset(
    {
        "identifier",
        "property_identifier",
        "shorthand_property_identifier",
        "type_identifier",
    }
)

LANGUAGE_CONFIG: dict[str, LanguageConfig] = {
    "python": LanguageConfig(
        extensions=(".py",),
        callable_types=("function", "method"),
        analyzer_factory=_python_analyzer_factory,
        module_namer=_python_module_namer,
    ),
    "typescript": LanguageConfig(
        extensions=(".ts", ".tsx"),
        callable_types=("function", "method"),
        analyzer_factory=_typescript_analyzer_factory,
        module_namer=_typescript_module_namer,
    ),
    "java": LanguageConfig(
        extensions=(".java",),
        callable_types=("method",),
        analyzer_factory=_java_analyzer_factory,
        module_namer=_java_module_namer,
    ),
}
