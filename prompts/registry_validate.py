"""Prompt registry validation helpers."""
from __future__ import annotations

import inspect
from pathlib import Path, PurePosixPath
from typing import Optional

from ..reducers.registry import load_reducer
from ..runtime.logging import get_logger
from .specs import load_spec_text, validate_placeholder_bijection

_LOGGER = get_logger("prompts.registry")
_ALLOWED_KINDS = {"core", "addon", "internal", "user"}


def _registry_error(message: str) -> None:
    _LOGGER.error(message)
    raise ValueError(message)


def _validate_list(label: str, value: object, prompt_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        _registry_error(f"Prompt '{prompt_name}' has invalid {label}; expected list.")
    for entry in value:
        if not isinstance(entry, str) or not entry:
            _registry_error(f"Prompt '{prompt_name}' has invalid {label} entry.")
    return list(value)


def _validate_default_args(value: object, prompt_name: str) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        _registry_error(f"Prompt '{prompt_name}' has invalid default_args; expected mapping.")
    for key in value.keys():
        if not isinstance(key, str) or not key:
            _registry_error(f"Prompt '{prompt_name}' has invalid default_args key.")
    return dict(value)


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
        _registry_error(
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


def _validate_entry(
    prompt_name: str,
    entry: dict[str, object],
    *,
    repo_root: Optional[Path],
    source: str,
) -> None:
    kind = entry.get("kind")
    if kind is None:
        entry["kind"] = "user"
        kind = "user"
    if kind not in _ALLOWED_KINDS:
        _registry_error(f"Prompt '{prompt_name}' has invalid kind '{kind}'.")
    if "spec" not in entry and "wording" not in entry:
        _registry_error(f"Prompt '{prompt_name}' must declare spec or wording.")
    spec = entry.get("spec")
    wording = entry.get("wording")
    spec_root = entry.get("spec_root")
    if "spec" in entry and (not isinstance(spec, str) or not spec):
        _registry_error(f"Prompt '{prompt_name}' has invalid spec path.")
    if "wording" in entry and (not isinstance(wording, str) or not wording.strip()):
        _registry_error(f"Prompt '{prompt_name}' has invalid wording.")
    if spec_root is not None and (not isinstance(spec_root, str) or not spec_root):
        _registry_error(f"Prompt '{prompt_name}' has invalid spec_root.")
    if isinstance(spec_root, str) and spec_root:
        spec_root_path = PurePosixPath(spec_root)
        if spec_root_path.is_absolute() or any(part == ".." for part in spec_root_path.parts):
            _registry_error(f"Prompt '{prompt_name}' has invalid spec_root path.")
    reducers = entry.get("reducers")
    if not isinstance(reducers, list) or not reducers:
        _registry_error(f"Prompt '{prompt_name}' must declare reducers.")
    required = _validate_list("required_args", entry.get("required_args"), prompt_name)
    optional = _validate_list("optional_args", entry.get("optional_args"), prompt_name)
    _validate_default_args(entry.get("default_args"), prompt_name)
    if len(set(required) | set(optional)) != len(required) + len(optional):
        _registry_error(f"Prompt '{prompt_name}' has duplicate argument names.")
    try:
        template = load_spec_text(entry, repo_root)
    except Exception as exc:
        _registry_error(f"Prompt '{prompt_name}' failed to load template: {exc}")
    reducer_modules = []
    for reducer_name in reducers:
        if not isinstance(reducer_name, str) or not reducer_name:
            _registry_error(f"Prompt '{prompt_name}' has invalid reducer name.")
        try:
            reducer_modules.append(load_reducer(reducer_name))
        except Exception as exc:
            _registry_error(f"Prompt '{prompt_name}' unknown reducer '{reducer_name}': {exc}")
    reducer_placeholders = []
    for reducer in reducer_modules:
        meta = getattr(reducer, "REDUCER_META", None)
        placeholders = getattr(meta, "placeholders", None)
        if not isinstance(placeholders, tuple) or not placeholders:
            _registry_error(
                f"Prompt '{prompt_name}' reducer '{reducer.__name__}' missing placeholders metadata."
            )
        if len(placeholders) != 1:
            _registry_error(
                f"Prompt '{prompt_name}' reducer '{reducer.__name__}' must define exactly one placeholder."
            )
        reducer_placeholders.extend(placeholders)
    try:
        validate_placeholder_bijection(
            template,
            reducer_placeholders,
            error_prefix=f"Prompt '{prompt_name}'",
        )
    except ValueError as exc:
        _registry_error(str(exc))
    _validate_reducer_arg_coverage(prompt_name, entry, reducer_modules)


def _validate_registry(
    entries: dict[str, dict[str, object]],
    *,
    repo_root: Optional[Path],
    source: str,
) -> None:
    for name, entry in entries.items():
        if not isinstance(entry, dict):
            _registry_error(f"Prompt '{name}' entry must be a mapping.")
        _validate_entry(name, entry, repo_root=repo_root, source=source)

