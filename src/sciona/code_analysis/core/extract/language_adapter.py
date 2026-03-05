# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Language adapter interfaces used by extraction registry boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from .analyzer import ASTAnalyzer
from ..normalize.model import FileSnapshot


ModuleNamer = Callable[[Path, FileSnapshot], str]
AnalyzerFactory = Callable[[], ASTAnalyzer]


class LanguageAdapter(Protocol):
    """Protocol contract for language analyzers."""

    language: str

    def analyze(self, snapshot: FileSnapshot, module_name: str): ...

    def module_name(self, repo_root: Path, snapshot: FileSnapshot) -> str: ...


@dataclass(frozen=True)
class LanguageDescriptor:
    """Static language wiring metadata consumed by the registry."""

    language_id: str
    extensions: tuple[str, ...]
    callable_types: tuple[str, ...]
    analyzer_factory: AnalyzerFactory | None
    module_namer: ModuleNamer | None
    install_hint: str | None = None


__all__ = [
    "AnalyzerFactory",
    "LanguageAdapter",
    "LanguageDescriptor",
    "ModuleNamer",
]
