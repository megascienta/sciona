"""Language adapter interfaces used by extraction registry boundaries."""

from . import language_registry
from .language_adapter import (
    AdapterSpecV1,
    AnalyzerFactory,
    LanguageAdapter,
    LanguageDescriptor,
    ModuleNamer,
)

__all__ = [
    "AdapterSpecV1",
    "AnalyzerFactory",
    "LanguageAdapter",
    "LanguageDescriptor",
    "ModuleNamer",
    "language_registry",
]
