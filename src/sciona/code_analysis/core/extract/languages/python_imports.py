# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Python Tree-sitter analyzer."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import List, Optional

from ....tools.tree_sitter import build_parser

from .....runtime import packaging as runtime_packaging
from .....runtime import paths as runtime_paths
from ...module_naming import module_name_from_path
from ....tools.call_extraction import collect_call_identifiers
from ...normalize.model import (
    AnalysisResult,
    CallRecord,
    EdgeRecord,
    FileSnapshot,
    SemanticNodeRecord,
)
from ..analyzer import ASTAnalyzer
from ..utils import count_lines

def module_name(repo_root: Path, snapshot: FileSnapshot) -> str:
    return _python_module_name(repo_root, snapshot)

def _python_module_name(repo_root: Path, snapshot: FileSnapshot) -> str:
    return module_name_from_path(
        repo_root,
        snapshot.record.relative_path,
        strip_suffix=True,
        treat_init_as_package=True,
    )

def _parse_imports(text: str) -> List[str]:
    modules: List[str] = []
    fragment = text.strip()
    if fragment.startswith("import "):
        targets = fragment[len("import ") :].split(",")
        for target in targets:
            candidate = target.strip()
            if not candidate:
                continue
            parts = candidate.split(" as ", 1)
            modules.append(parts[0].strip())
    elif fragment.startswith("from ") and " import " in fragment:
        prefix, _rest = fragment.split(" import ", 1)
        module = prefix[len("from ") :].strip()
        if module:
            modules.append(module)
    return modules

def _resolved_python_imports(
    fragment: str,
    module_name: str,
    is_package: bool,
    *,
    repo_prefix: str,
    local_packages: set[str],
) -> List[str]:
    raw_modules = _parse_imports(fragment)
    resolved: List[str] = []
    for candidate in raw_modules:
        resolved_module = _resolve_python_module_name(
            candidate,
            module_name,
            is_package,
            repo_prefix=repo_prefix,
            local_packages=local_packages,
        )
        if resolved_module:
            resolved.append(resolved_module)
    return resolved

def _resolve_python_module_name(
    target: str,
    module_name: str,
    is_package: bool,
    *,
    repo_prefix: str,
    local_packages: set[str],
) -> Optional[str]:
    target = target.strip()
    if not target:
        return None
    if target.startswith("."):
        package = _package_context(module_name, is_package)
        if not package:
            return None
        try:
            resolved = importlib.util.resolve_name(target, package)
            return resolved
        except ImportError:
            return None
    if repo_prefix and (target == repo_prefix or target.startswith(f"{repo_prefix}.")):
        return target
    for package in local_packages:
        if target == package or target.startswith(f"{package}."):
            return f"{repo_prefix}.{target}" if repo_prefix else target
    return target

def _package_context(module_name: str, is_package: bool) -> Optional[str]:
    if not module_name:
        return None
    if is_package:
        return module_name
    if "." in module_name:
        return module_name.rsplit(".", 1)[0]
    return None

def _repo_root_from_snapshot(snapshot: FileSnapshot) -> Path:
    rel_parts = snapshot.record.relative_path.parts
    if not rel_parts:
        return snapshot.record.path.parent
    return snapshot.record.path.parents[len(rel_parts) - 1]
