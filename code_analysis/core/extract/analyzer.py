"""Analyzer interface for ingestion languages."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..normalize.model import AnalysisResult, FileSnapshot


class ASTAnalyzer(ABC):
    language: str

    @abstractmethod
    def analyze(self, snapshot: FileSnapshot, module_name: str) -> AnalysisResult:
        """Produce semantic nodes and edges for the given file."""
        raise NotImplementedError

    @abstractmethod
    def module_name(self, repo_root: Path, snapshot: FileSnapshot) -> str:
        """Return module name for the given file."""
        raise NotImplementedError
