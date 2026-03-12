# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Analyzer interface for ingestion languages."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..normalize_model import AnalysisResult, FileSnapshot


class ASTAnalyzer(ABC):
    language: str
    module_index: set[str] | None

    def __init__(self) -> None:
        # Engines inject the in-scope module set before analyze() so analyzers can
        # classify internal imports consistently.
        self.module_index = None

    @abstractmethod
    def analyze(self, snapshot: FileSnapshot, module_name: str) -> AnalysisResult:
        """Produce semantic nodes and edges for the given file."""
        raise NotImplementedError

    @abstractmethod
    def module_name(self, repo_root: Path, snapshot: FileSnapshot) -> str:
        """Return module name for the given file."""
        raise NotImplementedError
