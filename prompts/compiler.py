"""Prompt compiler."""
from __future__ import annotations

from .registry import get_prompts
from .specs import load_spec_text, validate_placeholder_bijection
from ..reducers.registry import load_reducer


def compile_prompt(
    prompt_name: str,
    snapshot_id: str,
    conn,
    repo_root,
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
    reducer_args = dict(merged_args)
    if "callable_id" in merged_args and not (
        merged_args.get("function_id") or merged_args.get("method_id")
    ):
        reducer_args["function_id"] = merged_args["callable_id"]
    template = load_spec_text(entry, repo_root)
    reducers = [load_reducer(name) for name in entry["reducers"]]
    reducer_placeholders = []
    reducer_placeholder_map = []
    for reducer in reducers:
        meta = getattr(reducer, "REDUCER_META", None)
        placeholders = getattr(meta, "placeholders", None)
        if not isinstance(placeholders, tuple) or not placeholders:
            raise ValueError(
                f"PROMPT COMPILATION ERROR: Reducer '{reducer.__name__}' missing metadata placeholders."
            )
        reducer_placeholders.extend(placeholders)
        reducer_placeholder_map.append((reducer, placeholders))
    validate_placeholder_bijection(
        template,
        reducer_placeholders,
        error_prefix="PROMPT COMPILATION ERROR",
    )
    for reducer, placeholders in reducer_placeholder_map:
        if len(placeholders) != 1:
            raise ValueError(
                f"PROMPT COMPILATION ERROR: Reducer '{reducer.__name__}' must define exactly one placeholder."
            )
        value = reducer.render(snapshot_id, conn, repo_root, **reducer_args)
        template = template.replace(f"{{{placeholders[0]}}}", value)
    header_lines = [f"PROMPT: {prompt_name}"]
    header_lines.append(f"SNAPSHOT: {snapshot_id}")
    header = "\n".join(header_lines)
    return f"{header}\n\n{template}"


def _ensure_prompt_args_size(args: dict[str, object]) -> None:
    total_size = sum(len(str(value)) for value in args.values())
    if total_size > 100_000:
        raise ValueError("PROMPT COMPILATION ERROR: Prompt arguments too large.")
