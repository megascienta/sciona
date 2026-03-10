"""Naming helpers shared across language adapters."""

from .lexical_naming import LexicalNameDisambiguator
from .type_names import type_base_name

__all__ = ["LexicalNameDisambiguator", "type_base_name"]
