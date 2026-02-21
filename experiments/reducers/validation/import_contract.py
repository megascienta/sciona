# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from pathlib import Path

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
    if resolved:
        if resolved in module_names:
            return resolved
        if not require_in_repo:
            return resolved
    return None
