# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from pathlib import Path

from sciona.code_analysis.core.normalize.model import FileRecord, FileSnapshot
from sciona.code_analysis.core.extract.languages.python import _normalize_import
from sciona.code_analysis.core.extract.languages.typescript import _normalize_import as _normalize_ts_import
from sciona.code_analysis.core.extract.languages.java import (
    _normalize_import as _normalize_java_import,
    _module_prefix_for_package,
)


def _snapshot_for_file(
    repo_root: Path, file_path: str, language: str, *, content: bytes | None = None
) -> FileSnapshot:
    rel = Path(file_path)
    record = FileRecord(path=repo_root / rel, relative_path=rel, language=language)
    size = len(content) if content else 0
    return FileSnapshot(
        record=record,
        file_id="",
        blob_sha="",
        size=size,
        line_count=1,
        content=content,
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
        resolved = _normalize_import(
            raw_target,
            module_qname,
            is_package,
            repo_prefix=repo_prefix,
            local_packages=local_packages,
        )
    elif resolver == "typescript_normalize":
        snapshot = _snapshot_for_file(repo_root, file_path, language)
        resolved = _normalize_ts_import(raw_target, snapshot, module_qname)
    elif resolver == "java_normalize":
        abs_path = repo_root / Path(file_path)
        content = abs_path.read_bytes() if abs_path.exists() else None
        package_name = _java_package_name(content)
        module_prefix = _module_prefix_for_package(module_qname, package_name)
        snapshot = _snapshot_for_file(repo_root, file_path, language, content=content)
        fragment = raw_target
        if not raw_target.strip().startswith("import"):
            fragment = f"import {raw_target};"
        resolved = _normalize_java_import(
            fragment,
            module_qname,
            snapshot,
            module_prefix=module_prefix,
        )
    if resolved:
        if resolved in module_names:
            return resolved
        if not require_in_repo:
            return resolved
    return None
