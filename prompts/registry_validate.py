"""Prompt registry validation helpers."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Optional

from ..runtime.logging import debug_enabled, get_logger
from .specs import load_spec_text

_LOGGER = get_logger("prompts.registry")
_ALLOWED_KINDS = {"core", "addon", "internal", "user"}


def _registry_error(message: str) -> None:
    if debug_enabled():
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
        _registry_error(
            f"Prompt '{prompt_name}' has invalid default_args; expected mapping."
        )
    for key in value.keys():
        if not isinstance(key, str) or not key:
            _registry_error(f"Prompt '{prompt_name}' has invalid default_args key.")
    return dict(value)


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
        if spec_root_path.is_absolute() or any(
            part == ".." for part in spec_root_path.parts
        ):
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
        load_spec_text(entry, repo_root)
    except Exception as exc:
        _registry_error(f"Prompt '{prompt_name}' failed to load template: {exc}")


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
