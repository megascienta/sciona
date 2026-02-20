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
from ....tools.call_extraction import CallTarget, collect_call_targets
from ...normalize.model import (
    AnalysisResult,
    CallRecord,
    EdgeRecord,
    FileSnapshot,
    SemanticNodeRecord,
)
from ..analyzer import ASTAnalyzer
from ..utils import count_lines


class PythonAnalyzer(ASTAnalyzer):
    language = "python"

    def __init__(self) -> None:
        self._parser = build_parser("python")

    def analyze(self, snapshot: FileSnapshot, module_name: str) -> AnalysisResult:
        tree = self._parser.parse(snapshot.content)
        result = AnalysisResult()
        module_metadata = (
            {"status": "partial_parse"} if tree.root_node.has_error else None
        )
        module_node = SemanticNodeRecord(
            language=self.language,
            node_type="module",
            qualified_name=module_name,
            display_name=module_name.split(".")[-1],
            file_path=snapshot.record.relative_path,
            start_line=1,
            end_line=count_lines(snapshot.content),
            start_byte=0,
            end_byte=len(snapshot.content),
            metadata=module_metadata,
        )
        result.nodes.append(module_node)

        try:
            class_stack: List[str] = []
            module_functions: set[str] = set()
            class_methods: dict[str, set[str]] = {}
            pending_calls: list[tuple[str, str, object | None, str | None]] = []
            root = tree.root_node
            for child in root.children:
                self._walk(
                    node=child,
                    snapshot=snapshot,
                    module_name=module_name,
                    result=result,
                    class_stack=class_stack,
                    module_functions=module_functions,
                    class_methods=class_methods,
                    pending_calls=pending_calls,
                )
            (
                imports,
                import_aliases,
                member_aliases,
                raw_module_map,
            ) = _collect_imports(
                root,
                snapshot,
                module_name,
                module_index=getattr(self, "module_index", None),
            )
            for qualified, node_type, body_node, class_name in pending_calls:
                call_targets = collect_call_targets(
                    body_node,
                    snapshot.content,
                    call_node_types={"call"},
                    skip_node_types={"class_definition"},
                )
                resolved = _resolve_calls(
                    call_targets,
                    module_name,
                    module_functions,
                    class_methods,
                    class_name,
                    import_aliases,
                    member_aliases,
                    raw_module_map,
                )
                if resolved:
                    result.call_records.append(
                        CallRecord(
                            qualified_name=qualified,
                            node_type=node_type,
                            callee_identifiers=list(resolved),
                        )
                    )

            is_package = snapshot.record.path.name == "__init__.py"

            for module in sorted(set(imports)):
                result.edges.append(
                    EdgeRecord(
                        src_language=self.language,
                        src_node_type="module",
                        src_qualified_name=module_name,
                        dst_language=self.language,
                        dst_node_type="module",
                        dst_qualified_name=module,
                        edge_type="IMPORTS_DECLARED",
                    )
                )
        except Exception as exc:
            metadata = dict(module_node.metadata or {})
            metadata.update({"status": "partial_parse", "error": str(exc)})
            module_node.metadata = metadata
        return result

    def module_name(self, repo_root: Path, snapshot: FileSnapshot) -> str:
        return module_name(repo_root, snapshot)

    def _walk(
        self,
        node,
        snapshot: FileSnapshot,
        module_name: str,
        result: AnalysisResult,
        class_stack: List[str],
        module_functions: set[str],
        class_methods: dict[str, set[str]],
        pending_calls: list[tuple[str, str, object | None, str | None]],
    ) -> None:
        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if not name_node:
                return
            class_name = snapshot.content[
                name_node.start_byte : name_node.end_byte
            ].decode("utf-8")
            qualified = f"{module_name}.{class_name}"
            class_record = SemanticNodeRecord(
                language=self.language,
                node_type="class",
                qualified_name=qualified,
                display_name=class_name,
                file_path=snapshot.record.relative_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
            )
            result.nodes.append(class_record)
            result.edges.append(
                EdgeRecord(
                    src_language=self.language,
                    src_node_type="module",
                    src_qualified_name=module_name,
                    dst_language=self.language,
                    dst_node_type="class",
                    dst_qualified_name=qualified,
                    edge_type="CONTAINS",
                )
            )
            class_methods.setdefault(qualified, set())
            class_stack.append(qualified)
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    self._walk(
                        child,
                        snapshot,
                        module_name,
                        result,
                        class_stack,
                        module_functions,
                        class_methods,
                        pending_calls,
                    )
            class_stack.pop()
            return

        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if not name_node:
                return
            func_name = snapshot.content[
                name_node.start_byte : name_node.end_byte
            ].decode("utf-8")
            if class_stack:
                node_type = "method"
                parent = class_stack[-1]
                qualified = f"{parent}.{func_name}"
                parent_node_type = "class"
                edge_type = "DEFINES_METHOD"
                class_methods.setdefault(parent, set()).add(func_name)
            else:
                node_type = "function"
                parent = module_name
                parent_node_type = "module"
                qualified = f"{module_name}.{func_name}"
                edge_type = "CONTAINS"
                module_functions.add(func_name)
            record = SemanticNodeRecord(
                language=self.language,
                node_type=node_type,
                qualified_name=qualified,
                display_name=func_name,
                file_path=snapshot.record.relative_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
            )
            result.nodes.append(record)
            result.edges.append(
                EdgeRecord(
                    src_language=self.language,
                    src_node_type=parent_node_type,
                    src_qualified_name=parent,
                    dst_language=self.language,
                    dst_node_type=node_type,
                    dst_qualified_name=qualified,
                    edge_type=edge_type,
                )
            )
            body = node.child_by_field_name("body")
            pending_calls.append(
                (
                    qualified,
                    node_type,
                    body,
                    class_stack[-1] if class_stack else None,
                )
            )
            return

        for child in getattr(node, "children", []):
            self._walk(
                child,
                snapshot,
                module_name,
                result,
                class_stack,
                module_functions,
                class_methods,
                pending_calls,
            )


def module_name(repo_root: Path, snapshot: FileSnapshot) -> str:
    return module_name_from_path(
        repo_root,
        snapshot.record.relative_path,
        strip_suffix=True,
        treat_init_as_package=True,
    )


def _collect_imports(
    root,
    snapshot: FileSnapshot,
    module_name: str,
    *,
    module_index: set[str] | None,
) -> tuple[
    list[str],
    dict[str, str],
    dict[str, str],
    dict[str, str],
]:
    repo_root = _repo_root_from_snapshot(snapshot)
    repo_prefix = runtime_paths.repo_name_prefix(repo_root)
    local_packages = set(runtime_packaging.local_package_names(repo_root))
    imports: list[str] = []
    import_aliases: dict[str, str] = {}
    member_aliases: dict[str, str] = {}
    raw_module_map: dict[str, str] = {}
    is_package = snapshot.record.path.name == "__init__.py"
    for child in root.children:
        if child.type == "import_statement":
            segment = snapshot.content[child.start_byte : child.end_byte].decode("utf-8")
            for module, alias in _parse_import_statement(segment):
                normalized = _normalize_import(
                    module,
                    module_name,
                    is_package,
                    repo_prefix=repo_prefix,
                    local_packages=local_packages,
                )
                if not normalized or not _is_internal_module(
                    normalized, repo_prefix, module_index
                ):
                    continue
                imports.append(normalized)
                raw_module_map[module] = normalized
                if alias:
                    import_aliases[alias] = normalized
                elif "." not in module:
                    import_aliases[module] = normalized
        elif child.type == "import_from_statement":
            segment = snapshot.content[child.start_byte : child.end_byte].decode("utf-8")
            module, names = _parse_from_import(segment)
            if not module:
                continue
            normalized = _normalize_import(
                module,
                module_name,
                is_package,
                repo_prefix=repo_prefix,
                local_packages=local_packages,
            )
            if not normalized or not _is_internal_module(
                normalized, repo_prefix, module_index
            ):
                continue
            imports.append(normalized)
            raw_module_map[module] = normalized
            for name, alias in names:
                if name == "*":
                    continue
                member_aliases[alias or name] = f"{normalized}.{name}"
    return imports, import_aliases, member_aliases, raw_module_map


def _parse_import_statement(text: str) -> List[tuple[str, str | None]]:
    fragment = text.strip()
    if not fragment.startswith("import "):
        return []
    targets = fragment[len("import ") :].split(",")
    parsed: list[tuple[str, str | None]] = []
    for target in targets:
        candidate = target.strip()
        if not candidate:
            continue
        parts = candidate.split(" as ", 1)
        module = parts[0].strip()
        alias = parts[1].strip() if len(parts) == 2 else None
        if module:
            parsed.append((module, alias))
    return parsed


def _parse_from_import(text: str) -> tuple[str | None, List[tuple[str, str | None]]]:
    fragment = text.strip()
    if not fragment.startswith("from ") or " import " not in fragment:
        return None, []
    prefix, rest = fragment.split(" import ", 1)
    module = prefix[len("from ") :].strip()
    names: list[tuple[str, str | None]] = []
    for part in rest.split(","):
        piece = part.strip()
        if not piece:
            continue
        parts = piece.split(" as ", 1)
        name = parts[0].strip()
        alias = parts[1].strip() if len(parts) == 2 else None
        names.append((name, alias))
    return module or None, names


def _normalize_import(
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


def _resolve_calls(
    targets: List[CallTarget],
    module_name: str,
    module_functions: set[str],
    class_methods: dict[str, set[str]],
    class_name: str | None,
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    raw_module_map: dict[str, str],
) -> List[str]:
    resolved: list[str] = []
    class_method_names = class_methods.get(class_name, set()) if class_name else set()
    for target in targets:
        terminal = target.terminal
        callee_text = (target.callee_text or "").strip()
        if "." in callee_text:
            head, rest = callee_text.split(".", 1)
            if head in import_aliases:
                resolved.append(f"{import_aliases[head]}.{rest}")
                continue
            for raw, normalized in raw_module_map.items():
                if callee_text == raw or callee_text.startswith(f"{raw}."):
                    suffix = callee_text[len(raw) :].lstrip(".")
                    resolved.append(f"{normalized}.{suffix}" if suffix else normalized)
                    break
            else:
                pass
        if terminal in member_aliases:
            resolved.append(member_aliases[terminal])
            continue
        if class_name and _is_self_receiver(callee_text) and terminal in class_method_names:
            resolved.append(f"{class_name}.{terminal}")
            continue
        if _is_unqualified(callee_text) and terminal in module_functions:
            resolved.append(f"{module_name}.{terminal}")
            continue
        resolved.append(terminal)
    return resolved


def _is_unqualified(callee_text: str) -> bool:
    return "." not in callee_text


def _is_self_receiver(callee_text: str) -> bool:
    return callee_text.startswith("self.") or callee_text.startswith("cls.")


def _is_internal_module(
    module_name: str, repo_prefix: str, module_index: set[str] | None
) -> bool:
    if module_index is not None:
        return module_name in module_index
    return False




__all__ = [
    "PythonAnalyzer",
    "module_name",
]
