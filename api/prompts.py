"""Prompt API (stable)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..pipelines import prompt as prompt_pipeline
from ..pipelines import prompt_validation as prompt_validation_pipeline
from ..prompts import get_prompts
from ..prompts.registry_state import _register_addon_prompts, freeze_registry

ensure_prompt_preconditions = prompt_pipeline.ensure_prompt_preconditions
prompt_allows_answer = prompt_pipeline.prompt_allows_answer
compile_prompt_payload = prompt_pipeline.compile_prompt_payload
answer_prompt_text_by_name = prompt_pipeline.answer_prompt_text_by_name
extract_prompt_sections = prompt_pipeline.extract_prompt_sections


def register_addon_prompts(
    entries: dict[str, dict[str, object]],
    *,
    repo_root: Optional[Path] = None,
) -> None:
    _register_addon_prompts(entries, repo_root=repo_root)


__all__ = [
    "register_addon_prompts",
    "ensure_prompt_preconditions",
    "prompt_allows_answer",
    "compile_prompt_payload",
    "answer_prompt_text_by_name",
    "extract_prompt_sections",
    "freeze_registry",
    "get_prompts",
    "validate_prompt_entry",
]
validate_prompt_entry = prompt_validation_pipeline.validate_prompt_entry
