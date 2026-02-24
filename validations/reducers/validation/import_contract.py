# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
from pathlib import Path

from sciona.runtime.paths import repo_name_prefix

from .independent.contract_normalization import (
    module_prefix_for_java_package,
    normalize_java_import,
    normalize_python_import,
    normalize_typescript_import,
    normalize_typescript_relative_index,
)

def _java_package_name(content: bytes | None) -> str | None:
    if not content:
        return None
    for line in content.splitlines():
        text = line.decode("utf-8", errors="ignore").strip()
        if not text or text.startswith("//"):
            continue
        if text.startswith("package ") and text.endswith(";"):
            return text[len("package ") : -1].strip() or None
        if text.startswith("import "):
            break
    return None


def _load_tsconfig(repo_root: Path) -> dict:
    tsconfig = repo_root / "tsconfig.json"
    if not tsconfig.exists():
        return {}
    try:
        data = json.loads(tsconfig.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    compiler = data.get("compilerOptions")
    if not isinstance(compiler, dict):
        return {}
    paths = compiler.get("paths")
    if not isinstance(paths, dict):
        return {}
    base_url = compiler.get("baseUrl")
    if not isinstance(base_url, str):
        base_url = "."
    aliases: dict[str, list[str]] = {}
    for key, value in paths.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, list):
            entries = [item for item in value if isinstance(item, str) and item.strip()]
            if entries:
                aliases[key] = entries
    return {"base_url": base_url, "paths": aliases}


def _rewrite_repo_prefix(resolved: str | None, repo_root: Path, repo_prefix: str) -> str | None:
    if not resolved:
        return resolved
    actual_prefix = repo_name_prefix(repo_root)
    if (
        actual_prefix
        and repo_prefix
        and actual_prefix != repo_prefix
        and (resolved == actual_prefix or resolved.startswith(f"{actual_prefix}."))
    ):
        suffix = resolved[len(actual_prefix) :]
        if suffix.startswith("."):
            return f"{repo_prefix}{suffix}"
        return repo_prefix
    return resolved


def _ts_path_alias_candidates(
    specifier: str,
    repo_root: Path,
) -> list[str]:
    config = _load_tsconfig(repo_root)
    base_url = config.get("base_url") or "."
    aliases = config.get("paths") or {}
    if not aliases:
        return []
    candidates: list[str] = []
    for key, targets in aliases.items():
        replacement: str | None = None
        if "*" in key:
            k_prefix, k_suffix = key.split("*", 1)
            if not specifier.startswith(k_prefix):
                continue
            if k_suffix and not specifier.endswith(k_suffix):
                continue
            replacement = specifier[len(k_prefix) :]
            if k_suffix:
                replacement = replacement[: -len(k_suffix)]
        else:
            if specifier != key:
                continue
            replacement = ""
        for target in targets:
            mapped = target
            if "*" in target:
                t_prefix, t_suffix = target.split("*", 1)
                mapped = f"{t_prefix}{replacement}{t_suffix}"
            base_prefix = base_url.strip().strip("/")
            path = mapped.strip().strip("/")
            if base_prefix and not mapped.startswith(("/", "./", "../")):
                path = f"{base_prefix}/{path}" if path else base_prefix
            candidates.append(path)
            candidates.append(f"{path}/index")
    deduped: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        key = item.strip("/")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    return deduped


def resolve_import_contract(
    raw_target: str,
    file_path: str,
    module_qname: str,
    language: str,
    contract: dict,
    module_names: set[str],
    repo_root: Path,
    repo_prefix: str,
    local_packages: set[str],
) -> str | None:
    if not raw_target:
        return None
    imports_spec = contract.get("imports", {})
    require_in_repo = imports_spec.get("require_module_in_repo", True)
    language_spec = (imports_spec.get("languages") or {}).get(language, {})
    resolver = language_spec.get("resolver")
    if not resolver:
        return None
    resolved = None
    if resolver == "python_resolve":
        is_package = Path(file_path).name == "__init__.py"
        resolved = normalize_python_import(
            raw_target,
            module_qname,
            is_package,
            repo_prefix=repo_prefix,
            local_packages=local_packages,
        )
    elif resolver == "typescript_normalize":
        resolved = normalize_typescript_import(raw_target, file_path, repo_root)
        if (
            (not resolved or resolved not in module_names)
            and raw_target.strip().startswith(".")
        ):
            alt = normalize_typescript_relative_index(raw_target, file_path, repo_root)
            if alt:
                resolved = alt
        if (not resolved or resolved not in module_names) and not raw_target.strip().startswith("."):
            for alias_path in _ts_path_alias_candidates(raw_target.strip(), repo_root):
                alias_resolved = normalize_typescript_import(
                    f"./{alias_path}",
                    file_path="__tsconfig_root__.ts",
                    repo_root=repo_root,
                )
                alias_resolved = _rewrite_repo_prefix(alias_resolved, repo_root, repo_prefix)
                if alias_resolved and alias_resolved in module_names:
                    resolved = alias_resolved
                    break
    elif resolver == "java_normalize":
        abs_path = repo_root / Path(file_path)
        content = abs_path.read_bytes() if abs_path.exists() else None
        package_name = _java_package_name(content)
        module_prefix = module_prefix_for_java_package(module_qname, package_name)
        fragment = raw_target
        if not raw_target.strip().startswith("import"):
            fragment = f"import {raw_target};"
        resolved = normalize_java_import(
            fragment,
            module_qname,
            module_prefix=module_prefix,
            repo_prefix=repo_prefix,
        )
    resolved = _rewrite_repo_prefix(resolved, repo_root, repo_prefix)
    if resolved:
        if resolved in module_names:
            return resolved
        if not require_in_repo:
            return resolved
    return None
