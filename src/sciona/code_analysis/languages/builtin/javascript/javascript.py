# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""JavaScript Tree-sitter analyzer (initial wiring)."""

from __future__ import annotations

from pathlib import Path

from ....core.module_naming import module_name_from_path
from ....core.normalize.model import AnalysisResult, FileSnapshot, SemanticNodeRecord
from ....core.extract.analyzer import ASTAnalyzer
from ....core.extract.ir.extraction_buffer import ExtractionBuffer
from ....core.extract.parsing.parser_bootstrap import bootstrap_tree_sitter_parser
from ....core.extract.parsing.query_helpers import count_lines


class JavaScriptAnalyzer(ASTAnalyzer):
    language = "javascript"

    def __init__(self) -> None:
        self._parser, _language, diagnostics = bootstrap_tree_sitter_parser("javascript")
        self._parser_bootstrap_diagnostics = diagnostics

    def analyze(self, snapshot: FileSnapshot, module_name: str) -> AnalysisResult:
        # Parse eagerly to ensure parser diagnostics and fail-closed behavior.
        self._parser.parse(snapshot.content)
        buffer = ExtractionBuffer()
        buffer.add_node(
            SemanticNodeRecord(
                language=self.language,
                node_type="module",
                qualified_name=module_name,
                display_name=module_name.split(".")[-1],
                file_path=snapshot.record.relative_path,
                start_line=1,
                end_line=count_lines(snapshot.content),
                start_byte=0,
                end_byte=len(snapshot.content),
            )
        )
        return buffer.finalize()

    def module_name(self, repo_root: Path, snapshot: FileSnapshot) -> str:
        return module_name(repo_root, snapshot)


def module_name(repo_root: Path, snapshot: FileSnapshot) -> str:
    raw = module_name_from_path(
        repo_root,
        snapshot.record.relative_path,
        strip_suffix=False,
        treat_init_as_package=False,
    )
    if raw.endswith(".mjs"):
        return raw[: -len(".mjs")]
    if raw.endswith(".cjs"):
        return raw[: -len(".cjs")]
    if raw.endswith(".js"):
        return raw[: -len(".js")]
    return raw


__all__ = ["JavaScriptAnalyzer", "module_name"]
