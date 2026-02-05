"""Prompt reducer validation helpers."""
from __future__ import annotations

import inspect
from pathlib import Path
from typing import Optional

from ..prompts.specs import load_spec_text, validate_placeholder_bijection
from ..reducers.registry import load_reducer
from ..runtime.logging import get_logger

_LOGGER = get_logger("pipelines.prompts")


def _reducer_arg_info(reducer) -> tuple[set[str], set[str]]:
    render = getattr(reducer, "render", None)
    if render is None:
        return set(), set()
    signature = inspect.signature(render)
    required: set[str] = set()
    optional: set[str] = set()
    for name, param in signature.parameters.items():
        if name in {"snapshot_id", "conn", "repo_root"}:
            continue
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            continue
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            continue
        if param.default is inspect._empty:
            required.add(name)
        else:
            optional.add(name)
    return required, optional


def _validate_reducer_arg_coverage(
    prompt_name: str,
    entry: dict[str, object],
    reducers: list,
) -> None:
    prompt_args = set()
    prompt_args.update(entry.get("required_args") or [])
    prompt_args.update(entry.get("optional_args") or [])
    prompt_args.update((entry.get("default_args") or {}).keys())
    reducer_required: set[str] = set()
    reducer_optional: set[str] = set()
    for reducer in reducers:
        required, optional = _reducer_arg_info(reducer)
        reducer_required.update(required)
        reducer_optional.update(optional)
    missing_required = sorted(arg for arg in reducer_required if arg not in prompt_args)
    if missing_required:
        missing = ", ".join(missing_required)
        raise ValueError(
            f"Prompt '{prompt_name}' is missing required args for reducer use: {missing}."
        )
    unused_args = sorted(arg for arg in prompt_args if arg not in reducer_required | reducer_optional)
    if unused_args:
        unused = ", ".join(unused_args)
        _LOGGER.warning(
            "Prompt '%s' declares args unused by reducers: %s.",
            prompt_name,
            unused,
        )


def resolve_prompt_reducers(
    prompt_name: str,
    entry: dict[str, object],
    *,
    repo_root: Optional[Path],
) -> list[tuple[object, str]]:
    reducers = entry.get("reducers")
    if not isinstance(reducers, (list, tuple)) or not reducers:
        raise ValueError(f"Prompt '{prompt_name}' must declare reducers.")
    reducers = list(reducers)
    template = load_spec_text(entry, repo_root)
    reducer_modules = []
    for reducer_name in reducers:
        if not isinstance(reducer_name, str) or not reducer_name:
            raise ValueError(f"Prompt '{prompt_name}' has invalid reducer name.")
        try:
            reducer_modules.append(load_reducer(reducer_name))
        except Exception as exc:
            raise ValueError(f"Prompt '{prompt_name}' unknown reducer '{reducer_name}': {exc}") from exc
    reducer_placeholders = []
    reducer_placeholder_pairs: list[tuple[object, str]] = []
    for reducer in reducer_modules:
        meta = getattr(reducer, "REDUCER_META", None)
        placeholders = getattr(meta, "placeholders", None)
        if not isinstance(placeholders, tuple) or not placeholders:
            raise ValueError(
                f"Prompt '{prompt_name}' reducer '{reducer.__name__}' missing placeholders metadata."
            )
        if len(placeholders) != 1:
            raise ValueError(
                f"Prompt '{prompt_name}' reducer '{reducer.__name__}' must define exactly one placeholder."
            )
        placeholder = placeholders[0]
        reducer_placeholders.append(placeholder)
        reducer_placeholder_pairs.append((reducer, placeholder))
    validate_placeholder_bijection(
        template,
        reducer_placeholders,
        error_prefix=f"Prompt '{prompt_name}'",
    )
    _validate_reducer_arg_coverage(prompt_name, entry, reducer_modules)
    return reducer_placeholder_pairs


def validate_prompt_entry(
    prompt_name: str,
    entry: dict[str, object],
    *,
    repo_root: Optional[Path],
) -> None:
    """Validate prompt reducer wiring without rendering payloads."""
    resolve_prompt_reducers(prompt_name, entry, repo_root=repo_root)


__all__ = ["resolve_prompt_reducers", "validate_prompt_entry"]
