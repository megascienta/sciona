# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Tree-sitter parser bootstrap helper."""

from __future__ import annotations

from tree_sitter import Parser
from tree_sitter_languages import get_language


def bootstrap_tree_sitter_parser(language_name: str) -> tuple[Parser, object, dict[str, object]]:
    """Return a parser/language pair and setup diagnostics for one grammar."""
    parser = Parser()
    language = get_language(language_name)
    if hasattr(parser, "set_language"):
        parser.set_language(language)
        binding_api = "set_language"
    else:
        parser.language = language
        binding_api = "language_attr"
    diagnostics: dict[str, object] = {
        "language_name": language_name,
        "binding_api": binding_api,
        "query_api_available": hasattr(language, "query"),
        "parser_class": type(parser).__name__,
        "language_class": type(language).__name__,
        "language_module": type(language).__module__,
        "language_version": getattr(language, "version", None),
        "language_abi_version": getattr(language, "abi_version", None),
    }
    return parser, language, diagnostics


__all__ = ["bootstrap_tree_sitter_parser"]
