# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from pathlib import Path

from sciona.code_analysis.core.normalize.model import FileRecord, FileSnapshot
from sciona.code_analysis.core.extract.languages.python_imports import (
    _resolve_python_module_name,
)
from sciona.code_analysis.core.extract.languages.typescript import _normalize_ts_import
from sciona.code_analysis.core.extract.languages.java import _normalize_java_import


def _snapshot_for_file(repo_root: Path, file_path: str, language: str) -> FileSnapshot:
    rel = Path(file_path)
    record = FileRecord(path=repo_root / rel, relative_path=rel, language=language)
    return FileSnapshot(record=record, file_id="", blob_sha="", size=0, line_count=1, content=None)


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
        resolved = _resolve_python_module_name(
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
        snapshot = _snapshot_for_file(repo_root, file_path, language)
        fragment = raw_target
        if not raw_target.strip().startswith("import"):
            fragment = f"import {raw_target};"
        resolved = _normalize_java_import(fragment, module_qname, snapshot)
    if resolved:
        if resolved in module_names:
            return resolved
        if not require_in_repo:
            return resolved
    return None
