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


@dataclass(frozen=True)
class AdapterSpecV1:
    """Versioned language adapter contract used by onboarding and validation."""

    language_id: str
    extensions: tuple[str, ...]
    grammar_name: str
    query_set_version: int
    callable_types: tuple[str, ...]
    module_namer: ModuleNamer
    extractor_factory: AnalyzerFactory
    capability_manifest_key: str


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
    extractor_factory: AnalyzerFactory | None
    module_namer: ModuleNamer | None
    grammar_name: str | None = None
    query_set_version: int | None = None
    capability_manifest_key: str | None = None
    install_hint: str | None = None

    @property
    def analyzer_factory(self) -> AnalyzerFactory | None:
        """Backward-compatible alias for pre-refactor callsites/tests."""
        return self.extractor_factory

    def to_adapter_spec_v1(self) -> AdapterSpecV1 | None:
        if (
            self.extractor_factory is None
            or self.module_namer is None
            or not self.grammar_name
            or self.query_set_version is None
            or not self.capability_manifest_key
        ):
            return None
        return AdapterSpecV1(
            language_id=self.language_id,
            extensions=self.extensions,
            grammar_name=self.grammar_name,
            query_set_version=self.query_set_version,
            callable_types=self.callable_types,
            module_namer=self.module_namer,
            extractor_factory=self.extractor_factory,
            capability_manifest_key=self.capability_manifest_key,
        )


__all__ = [
    "AdapterSpecV1",
    "AnalyzerFactory",
    "LanguageAdapter",
    "LanguageDescriptor",
    "ModuleNamer",
]
