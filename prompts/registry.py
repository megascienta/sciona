"""Prompt registry accessors (facade)."""
from __future__ import annotations

from .registry_state import get_prompts, registry_frozen

__all__ = ["get_prompts", "registry_frozen"]
