"""Import and symbol intermediate representations for language adapters."""

from .import_model import NormalizedImportModel
from .local_binding_ir import (
    ALLOWED_BINDING_EVIDENCE,
    ALLOWED_BINDING_KINDS,
    ALLOWED_BINDING_PRECEDENCE,
    FORBIDDEN_DYNAMIC_SHAPES,
    LocalBindingFact,
    validated_local_binding_fact,
)
from .symbol_ir import TypedSymbolBinding, resolve_alias

__all__ = [
    "ALLOWED_BINDING_EVIDENCE",
    "ALLOWED_BINDING_KINDS",
    "ALLOWED_BINDING_PRECEDENCE",
    "FORBIDDEN_DYNAMIC_SHAPES",
    "LocalBindingFact",
    "NormalizedImportModel",
    "TypedSymbolBinding",
    "resolve_alias",
    "validated_local_binding_fact",
]
