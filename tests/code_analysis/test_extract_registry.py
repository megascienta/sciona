# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.code_analysis.core.extract.registry import (
    extensions_for_language,
    get_analyzer,
    get_analyzer_for_path,
    language_for_extension,
)


def test_extensions_for_language_includes_python() -> None:
    assert ".py" in extensions_for_language("python")
    assert ".js" in extensions_for_language("javascript")


def test_get_analyzer_returns_instance() -> None:
    analyzer = get_analyzer("python")
    assert analyzer is not None
    assert hasattr(analyzer, "analyze")


def test_language_for_extension_respects_enabled_languages() -> None:
    assert language_for_extension(".py", ["python", "java"]) == "python"
    assert language_for_extension(".java", ["python", "java"]) == "java"
    assert language_for_extension(".js", ["javascript", "java"]) == "javascript"
    assert language_for_extension(".rb", ["python"]) is None


def test_get_analyzer_for_path_resolves_by_extension() -> None:
    analyzers = {"python": object()}
    assert get_analyzer_for_path(Path("script.py"), analyzers) is analyzers["python"]
    assert get_analyzer_for_path(Path("script.java"), analyzers) is None
    assert get_analyzer_for_path(Path("script.unknown"), analyzers) is None
