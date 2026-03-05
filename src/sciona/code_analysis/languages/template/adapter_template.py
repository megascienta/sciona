# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Starter template for new language adapter wiring."""

from __future__ import annotations

from pathlib import Path

from ...core.extract.analyzer import ASTAnalyzer
from ...core.normalize.model import AnalysisResult, FileSnapshot


class TemplateAnalyzer(ASTAnalyzer):
    language = "template"

    def analyze(self, snapshot: FileSnapshot, module_name: str) -> AnalysisResult:
        # Replace with language-specific extraction that emits contract nodes/edges.
        return AnalysisResult()

    def module_name(self, repo_root: Path, snapshot: FileSnapshot) -> str:
        # Replace with canonical module naming for the language.
        return snapshot.record.relative_path.as_posix()


def extractor_factory() -> ASTAnalyzer:
    return TemplateAnalyzer()


def module_namer(repo_root: Path, snapshot: FileSnapshot) -> str:
    return TemplateAnalyzer().module_name(repo_root, snapshot)


__all__ = ["TemplateAnalyzer", "extractor_factory", "module_namer"]
