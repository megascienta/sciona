"""Identifier resolution API (stable)."""

from __future__ import annotations

from ..pipelines import resolve as resolve_pipeline

identifier_for_repo = resolve_pipeline.identifier_for_repo
identifier = resolve_pipeline.identifier
require_identifier = resolve_pipeline.require_identifier
format_resolution_message = resolve_pipeline.format_resolution_message

__all__ = [
    "identifier_for_repo",
    "identifier",
    "require_identifier",
    "format_resolution_message",
]
