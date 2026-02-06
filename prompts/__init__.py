"""Minimal prompt compiler."""

from __future__ import annotations

from .compiler import compile_prompt
from .registry import get_prompts

__all__ = ["compile_prompt", "get_prompts"]
