# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Java Tree-sitter analyzer."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ....tools.tree_sitter import build_parser

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
from ..utils import count_lines, find_nodes_of_type
from .....runtime import paths as runtime_paths


class JavaAnalyzer(ASTAnalyzer):
    language = "java"

    def __init__(self) -> None:
        self._parser = build_parser("java")

    def analyze(self, snapshot: FileSnapshot, module_name: str) -> AnalysisResult:
        tree = self._parser.parse(snapshot.content)
        result = AnalysisResult()
        module_metadata: dict[str, object] | None = (
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
            root = tree.root_node
            package_name = _extract_package(root, snapshot.content)
            module_prefix = _module_prefix_for_package(module_name, package_name)
            if package_name:
                if module_metadata is None:
                    module_metadata = {"package": package_name}
                else:
                    module_metadata["package"] = package_name
                module_node.metadata = module_metadata
            module_functions: set[str] = set()
            class_methods: dict[str, set[str]] = {}
            class_name_map: dict[str, str] = {}
            import_class_map: dict[str, str] = {}
            pending_calls: list[tuple[str, str, object | None, str | None]] = []
            for child in root.children:
                self._walk(
                    child,
                    snapshot,
                    module_name,
                    result,
                    class_stack,
                    module_functions,
                    class_methods,
                    class_name_map,
                    pending_calls,
                )
            resolved_calls: list[tuple[str, str, List[str]]] = []
            for qualified, node_type, body_node, class_name in pending_calls:
                call_targets = collect_call_targets(
                    body_node,
                    snapshot.content,
                    call_node_types={
                        "method_invocation",
                        "object_creation_expression",
                        "explicit_constructor_invocation",
                        "constructor_invocation",
                        "super_constructor_invocation",
                        "this_constructor_invocation",
                    },
                    skip_node_types={
                        "class_declaration",
                        "interface_declaration",
                        "enum_declaration",
                        "record_declaration",
                    },
                    callee_field_names=("name", "type", "function"),
                    callee_renderer=_callee_text,
                )
                resolved = _resolve_java_calls(
                    call_targets,
                    module_name,
                    module_functions,
                    class_methods,
                    class_name_map,
                    import_class_map,
                    class_name,
                )
                if resolved:
                    resolved_calls.append((qualified, node_type, list(resolved)))
            if resolved_calls:
                normalized = _normalize_call_identifiers(resolved_calls)
                for qualified, node_type, callee_identifiers in normalized:
                    result.call_records.append(
                        CallRecord(
                            qualified_name=qualified,
                            node_type=node_type,
                            callee_identifiers=callee_identifiers,
                        )
                    )

            imports: List[str] = []
            for import_node in find_nodes_of_type(root, "import_declaration"):
                fragment = snapshot.content[
                    import_node.start_byte : import_node.end_byte
                ].decode("utf-8")
                normalized = _normalize_import(
                    fragment,
                    module_name,
                    snapshot,
                    module_prefix=module_prefix,
                )
                if not normalized:
                    continue
                if not _is_internal_module(
                    normalized,
                    runtime_paths.repo_name_prefix(_repo_root_from_snapshot(snapshot)),
                    getattr(self, "module_index", None),
                ):
                    continue
                imports.append(normalized)
                simple_name = _import_simple_name(fragment)
                if simple_name:
                    import_class_map[simple_name] = normalized

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
        return module_name_from_path(
            repo_root,
            snapshot.record.relative_path,
            strip_suffix=True,
            treat_init_as_package=False,
        )

    def _walk(
        self,
        node,
        snapshot: FileSnapshot,
        module_name: str,
        result: AnalysisResult,
        class_stack: List[str],
        module_functions: set[str],
        class_methods: dict[str, set[str]],
        class_name_map: dict[str, str],
        pending_calls: list[tuple[str, str, object | None, str | None]],
    ) -> None:
        if node.type in {
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
            "record_declaration",
        }:
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
            body = node.child_by_field_name("body")
            class_stack.append(qualified)
            class_methods.setdefault(qualified, set())
            class_name_map.setdefault(class_name, qualified)
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
                        class_name_map,
                        pending_calls,
                    )
            class_stack.pop()
            return

        if node.type in {
            "method_declaration",
            "constructor_declaration",
            "compact_constructor_declaration",
        }:
            name_node = node.child_by_field_name("name")
            if not name_node:
                return
            func_name = snapshot.content[
                name_node.start_byte : name_node.end_byte
            ].decode("utf-8")
            if not class_stack:
                return
            node_type = "method"
            parent = class_stack[-1]
            parent_node_type = "class"
            qualified = f"{parent}.{func_name}"
            edge_type = "DEFINES_METHOD"
            class_methods.setdefault(parent, set()).add(func_name)
            result.nodes.append(
                SemanticNodeRecord(
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
            )
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
            body_node = node.child_by_field_name("body")
            pending_calls.append(
                (
                    qualified,
                    node_type,
                    body_node,
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
                class_name_map,
                pending_calls,
            )


def module_name(repo_root: Path, snapshot: FileSnapshot) -> str:
    return module_name_from_path(
        repo_root,
        snapshot.record.relative_path,
        strip_suffix=True,
        treat_init_as_package=False,
    )


def _normalize_import(
    fragment: str,
    module_name: str,
    snapshot: FileSnapshot,
    *,
    module_prefix: str | None,
) -> Optional[str]:
    raw = fragment.strip()
    if not raw.startswith("import"):
        return None
    is_static = raw.startswith("import static")
    text = raw[len("import") :].strip()
    if text.startswith("static"):
        text = text[len("static") :].strip()
    if text.endswith(";"):
        text = text[:-1]
    text = text.strip()
    if text.endswith(".*"):
        # Package-level wildcard imports are not resolvable to a single module.
        return None
    text = text.strip()
    if not text:
        return None
    if is_static and "." in text:
        # Drop static member suffix to point at the declaring type.
        text = text.rsplit(".", 1)[0]
    repo_root = _repo_root_from_snapshot(snapshot)
    repo_prefix = runtime_paths.repo_name_prefix(repo_root)
    if repo_prefix and (text == repo_prefix or text.startswith(f"{repo_prefix}.")):
        return text
    top_package = _top_level_package(module_name, repo_prefix)
    if top_package and (text == top_package or text.startswith(f"{top_package}.")):
        return f"{repo_prefix}.{text}" if repo_prefix else text
    if module_prefix:
        return f"{module_prefix}.{text}"
    return text


def _import_simple_name(fragment: str) -> str | None:
    raw = fragment.strip()
    if not raw.startswith("import"):
        return None
    is_static = raw.startswith("import static")
    text = raw[len("import") :].strip()
    if text.startswith("static"):
        text = text[len("static") :].strip()
    if text.endswith(";"):
        text = text[:-1].strip()
    if text.endswith(".*"):
        return None
    if is_static and "." in text:
        text = text.rsplit(".", 1)[0]
    if not text:
        return None
    return text.split(".")[-1]


def _top_level_package(module_name: str, repo_prefix: str) -> str | None:
    if repo_prefix and (
        module_name == repo_prefix or module_name.startswith(f"{repo_prefix}.")
    ):
        remainder = module_name[len(repo_prefix) + 1 :]
    else:
        remainder = module_name
    if not remainder:
        return None
    return remainder.split(".", 1)[0]


def _repo_root_from_snapshot(snapshot: FileSnapshot) -> Path:
    rel_parts = snapshot.record.relative_path.parts
    if not rel_parts:
        return snapshot.record.path.parent
    return snapshot.record.path.parents[len(rel_parts) - 1]


def _extract_package(root, content: bytes) -> Optional[str]:
    for node in find_nodes_of_type(root, "package_declaration"):
        fragment = content[node.start_byte : node.end_byte].decode("utf-8").strip()
        if not fragment.startswith("package"):
            continue
        fragment = fragment[len("package") :].strip()
        if fragment.endswith(";"):
            fragment = fragment[:-1].strip()
        return fragment or None
    return None


def _is_internal_module(
    module_name: str, repo_prefix: str, module_index: set[str] | None
) -> bool:
    if module_index is not None:
        return module_name in module_index
    if not repo_prefix:
        return True
    return module_name == repo_prefix or module_name.startswith(f"{repo_prefix}.")


def _normalize_call_identifiers(
    resolved_calls: list[tuple[str, str, List[str]]]
) -> list[tuple[str, str, List[str]]]:
    terminal_map: dict[str, str | None] = {}
    for _qualified, _node_type, identifiers in resolved_calls:
        for identifier in identifiers:
            if "." not in identifier:
                continue
            terminal = identifier.rsplit(".", 1)[-1]
            existing = terminal_map.get(terminal)
            if existing is None and terminal in terminal_map:
                continue
            if existing is None:
                terminal_map[terminal] = identifier
            elif existing != identifier:
                terminal_map[terminal] = None
    normalized: list[tuple[str, str, List[str]]] = []
    for qualified, node_type, identifiers in resolved_calls:
        updated: list[str] = []
        for identifier in identifiers:
            if "." in identifier:
                terminal = identifier.rsplit(".", 1)[-1]
                mapped = terminal_map.get(terminal)
                if mapped is None and terminal in terminal_map:
                    updated.append(terminal)
                elif mapped:
                    updated.append(mapped)
                else:
                    updated.append(identifier)
            else:
                mapped = terminal_map.get(identifier)
                if mapped:
                    updated.append(mapped)
                else:
                    updated.append(identifier)
        normalized.append((qualified, node_type, updated))
    return normalized


def _module_prefix_for_package(
    module_name: str, package_name: Optional[str]
) -> str | None:
    if not package_name:
        return None
    module_parts = module_name.split(".")
    package_parts = package_name.split(".")
    if len(module_parts) < len(package_parts):
        return None
    for idx in range(len(module_parts) - len(package_parts), -1, -1):
        if module_parts[idx : idx + len(package_parts)] == package_parts:
            prefix_parts = module_parts[:idx]
            return ".".join(prefix_parts) if prefix_parts else None
    return None


def _node_text(node, content: bytes) -> str | None:
    if node is None:
        return None
    return content[node.start_byte : node.end_byte].decode("utf-8")


def _callee_text(call_node, callee_node, content: bytes) -> str | None:
    if call_node is None:
        return _node_text(callee_node, content)
    if call_node.type == "method_invocation":
        name_node = call_node.child_by_field_name("name")
        object_node = call_node.child_by_field_name("object")
        name_text = _node_text(name_node or callee_node, content)
        if object_node is not None:
            object_text = _node_text(object_node, content)
            if object_text and name_text:
                return f"{object_text}.{name_text}"
        return name_text
    if call_node.type == "object_creation_expression":
        type_node = call_node.child_by_field_name("type")
        return _node_text(type_node, content) or _node_text(callee_node, content)
    return _node_text(callee_node, content)


def _resolve_java_calls(
    targets: List[CallTarget],
    module_name: str,
    module_functions: set[str],
    class_methods: dict[str, set[str]],
    class_name_map: dict[str, str],
    import_class_map: dict[str, str],
    class_name: str | None,
) -> List[str]:
    resolved: list[str] = []
    class_method_names = class_methods.get(class_name, set()) if class_name else set()
    for target in targets:
        terminal = target.terminal
        callee_text = (target.callee_text or "").strip()
        if _is_unqualified(callee_text):
            import_target = import_class_map.get(terminal)
            local_class = class_name_map.get(terminal)
            if import_target:
                resolved.append(f"{import_target}.{terminal}")
                continue
            if local_class:
                resolved.append(f"{local_class}.{terminal}")
                continue
        if class_name and terminal in class_method_names:
            if _is_receiver_call(callee_text) or _is_unqualified(callee_text):
                resolved.append(f"{class_name}.{terminal}")
                continue
        if _is_unqualified(callee_text) and terminal in module_functions:
            resolved.append(f"{module_name}.{terminal}")
            continue
        class_qualified = class_name_map.get(terminal)
        if class_qualified and terminal in class_methods.get(class_qualified, set()):
            resolved.append(f"{class_qualified}.{terminal}")
            continue
        resolved.append(terminal)
    return resolved


def _is_unqualified(callee_text: str) -> bool:
    return "." not in callee_text


def _is_receiver_call(callee_text: str) -> bool:
    return callee_text.startswith("this.") or callee_text.startswith("super.")
