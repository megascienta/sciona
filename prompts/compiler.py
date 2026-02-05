"""Prompt compiler."""
from __future__ import annotations

from typing import Mapping

from .registry import get_prompts
from .specs import load_spec_text, validate_placeholder_bijection


def compile_prompt(
    prompt_name: str,
    snapshot_id: str,
    repo_root,
    *,
    payloads: Mapping[str, str],
    **kwargs: object,
) -> str:
    prompts = get_prompts(repo_root)
    if prompt_name not in prompts:
        raise ValueError(f"PROMPT COMPILATION ERROR: Unknown prompt '{prompt_name}'.")
    entry = prompts[prompt_name]
    required_args = entry.get("required_args") or []
    optional_args = entry.get("optional_args") or []
    default_args = entry.get("default_args") or {}
    allowed_args = set(required_args) | set(optional_args) | set(default_args.keys())
    extra_args = [arg for arg in kwargs if arg not in allowed_args]
    if extra_args:
        extras = ", ".join(sorted(extra_args))
        raise ValueError(f"PROMPT COMPILATION ERROR: Unexpected prompt args: {extras}.")
    merged_args = {**default_args, **kwargs}
    _ensure_prompt_args_size(merged_args)
    missing_args = [arg for arg in required_args if merged_args.get(arg) is None]
    if missing_args:
        missing = ", ".join(missing_args)
        raise ValueError(f"PROMPT COMPILATION ERROR: Missing required prompt args: {missing}.")
    template = load_spec_text(entry, repo_root)
    validate_placeholder_bijection(
        template,
        list(payloads.keys()),
        error_prefix="PROMPT COMPILATION ERROR",
    )
    for placeholder, value in payloads.items():
        template = template.replace(f"{{{placeholder}}}", value)
    header_lines = [f"PROMPT: {prompt_name}"]
    header_lines.append(f"SNAPSHOT: {snapshot_id}")
    header = "\n".join(header_lines)
    return f"{header}\n\n{template}"


def _ensure_prompt_args_size(args: dict[str, object]) -> None:
    total_size = sum(len(str(value)) for value in args.values())
    if total_size > 100_000:
        raise ValueError("PROMPT COMPILATION ERROR: Prompt arguments too large.")
