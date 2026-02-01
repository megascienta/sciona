"""Prompt registry metadata."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Iterator, Mapping, Optional

import yaml
import inspect

from ..reducers.registry import load_reducer
from ..runtime import paths as runtime_paths
from ..runtime.errors import EnvError
from ..runtime.logging import get_logger
from .specs import load_spec_text, validate_placeholder_bijection

_LOGGER = get_logger("prompts.registry")
_ALLOWED_KINDS = {"core", "addon", "internal", "user"}
_FROZEN = False
_LAST_REPO_ROOT: Optional[Path] = None

_PROMPTS: dict[str, dict[str, object]] = {}
_ADDON_PROMPTS: dict[str, dict[str, object]] = {}
PROMPTS: Mapping[str, Mapping[str, object]] = _PROMPTS


def _registry_error(message: str) -> None:
    _LOGGER.error(message)
    raise ValueError(message)


def _resolve_repo_root(repo_root: Optional[Path]) -> Optional[Path]:
    if repo_root is None:
        try:
            return runtime_paths.get_repo_root()
        except EnvError:
            return None
    return repo_root


def _normalize_registry(raw: object, path: Path) -> dict[str, dict[str, object]]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        if "prompts" in raw and isinstance(raw["prompts"], dict):
            raw = raw["prompts"]
        entries: dict[str, dict[str, object]] = {}
        for name, entry in raw.items():
            if not isinstance(name, str) or not name:
                _registry_error(f"Invalid prompt name in {path}.")
            if not isinstance(entry, dict):
                _registry_error(f"Prompt '{name}' in {path} must be a mapping.")
            entries[name] = dict(entry)
        return entries
    if isinstance(raw, list):
        entries = {}
        for entry in raw:
            if not isinstance(entry, dict):
                _registry_error(f"Prompt entry in {path} must be a mapping.")
            name = entry.get("name")
            if not isinstance(name, str) or not name:
                _registry_error(f"Prompt entry in {path} missing 'name'.")
            if name in entries:
                _registry_error(f"Duplicate prompt name '{name}' in {path}.")
            normalized = dict(entry)
            normalized.pop("name", None)
            entries[name] = normalized
        return entries
    _registry_error(f"Invalid prompt registry format in {path}.")
    return {}


def _load_yaml_registry(path: Path, *, allow_missing: bool) -> dict[str, dict[str, object]]:
    if not path.exists():
        if allow_missing:
            return {}
        _registry_error(f"Missing prompt registry at {path}.")
    try:
        raw_text = path.read_text(encoding="utf-8")
        if len(raw_text.encode("utf-8")) > 1_000_000:
            _registry_error(f"Prompt registry {path} is too large.")
        raw = yaml.safe_load(raw_text) or {}
    except yaml.YAMLError as exc:
        _registry_error(f"Failed to parse prompt registry {path}: {exc}")
    except OSError as exc:
        _registry_error(f"Failed to read prompt registry {path}: {exc}")
    return _normalize_registry(raw, path)


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


def _load_registry(repo_root: Optional[Path]) -> dict[str, dict[str, object]]:
    repo_entries: dict[str, dict[str, object]] = {}
    if repo_root is not None:
        registry_path = runtime_paths.get_prompts_registry_path(repo_root)
        repo_entries = _load_yaml_registry(registry_path, allow_missing=True)
        if repo_entries:
            _validate_registry(repo_entries, repo_root=repo_root, source="repo")
    merged: dict[str, dict[str, object]] = {}
    for name, entry in repo_entries.items():
        if name in merged:
            _registry_error(f"Duplicate prompt name '{name}' in registry.")
        merged[name] = entry
    for name, entry in _ADDON_PROMPTS.items():
        if name in merged:
            _registry_error(f"Duplicate prompt name '{name}' in addon registry.")
        merged[name] = entry
    return merged


def _freeze_registry(entries: dict[str, dict[str, object]]) -> Mapping[str, Mapping[str, object]]:
    frozen: dict[str, Mapping[str, object]] = {}
    for name, entry in entries.items():
        frozen_entry: dict[str, object] = {}
        for key, value in entry.items():
            if isinstance(value, list):
                frozen_entry[key] = tuple(value)
            elif isinstance(value, dict):
                frozen_entry[key] = MappingProxyType(dict(value))
            else:
                frozen_entry[key] = value
        frozen[name] = MappingProxyType(frozen_entry)
    return MappingProxyType(frozen)


def _refresh_registry(repo_root: Optional[Path]) -> None:
    global _PROMPTS, PROMPTS, _LAST_REPO_ROOT
    if _LAST_REPO_ROOT == repo_root and _PROMPTS:
        return
    _PROMPTS = _load_registry(repo_root)
    PROMPTS = _freeze_registry(_PROMPTS) if _FROZEN else _PROMPTS
    _LAST_REPO_ROOT = repo_root


def get_prompts(repo_root: Optional[Path] = None) -> Mapping[str, Mapping[str, object]]:
    repo_root = _resolve_repo_root(repo_root)
    _refresh_registry(repo_root)
    return PROMPTS


def freeze_registry(repo_root: Optional[Path] = None) -> None:
    global PROMPTS, _FROZEN
    if _FROZEN:
        return
    repo_root = _resolve_repo_root(repo_root)
    _refresh_registry(repo_root)
    PROMPTS = _freeze_registry(_PROMPTS)
    _FROZEN = True


def registry_frozen() -> bool:
    return _FROZEN


@contextmanager
def mutable_registry(repo_root: Optional[Path] = None) -> Iterator[dict[str, dict[str, object]]]:
    """Temporarily expose a mutable registry (for tests only)."""
    global PROMPTS, _FROZEN
    repo_root = _resolve_repo_root(repo_root)
    _refresh_registry(repo_root)
    if _FROZEN:
        mutable: dict[str, dict[str, object]] = {}
        for name, entry in _PROMPTS.items():
            mutable[name] = dict(entry)
        PROMPTS = mutable
        _FROZEN = False
        try:
            yield mutable
        finally:
            _PROMPTS.clear()
            _PROMPTS.update(mutable)
            freeze_registry(repo_root)
    else:
        yield _PROMPTS


def register_addon_prompts(
    entries: dict[str, dict[str, object]],
    *,
    repo_root: Optional[Path] = None,
) -> None:
    if _FROZEN:
        raise RuntimeError("Cannot register addon prompts after registry is frozen.")
    if not entries:
        return
    repo_root = _resolve_repo_root(repo_root)
    _validate_registry(entries, repo_root=repo_root, source="addon")
    for name, entry in entries.items():
        normalized = dict(entry)
        normalized["_source"] = "addon"
        if name in _ADDON_PROMPTS:
            existing = _ADDON_PROMPTS[name]
            if existing == normalized:
                continue
            _registry_error(f"Duplicate addon prompt name '{name}'.")
        _ADDON_PROMPTS[name] = normalized
    _refresh_registry(repo_root)


__all__ = [
    "freeze_registry",
    "get_prompts",
    "mutable_registry",
    "registry_frozen",
    "register_addon_prompts",
]
