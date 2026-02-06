"""Tree-sitter adapter helpers."""

from __future__ import annotations

from tree_sitter import Parser
from tree_sitter_languages import get_language


def build_parser(language_name: str) -> Parser:
    parser = Parser()
    language = get_language(language_name)
    if hasattr(parser, "set_language"):
        parser.set_language(language)
    else:  # tree_sitter>=0.21 uses attribute assignment
        parser.language = language
    return parser
