# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Java Tree-sitter analyzer."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ....tools.tree_sitter import build_parser

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
            package_name = _extract_package_name(root, snapshot.content)
            if package_name:
                if module_metadata is None:
                    module_metadata = {"package": package_name}
                else:
                    module_metadata["package"] = package_name
                module_node.metadata = module_metadata
            for child in root.children:
                self._walk(child, snapshot, module_name, result, class_stack)

            imports: List[str] = []
            for import_node in find_nodes_of_type(root, "import_declaration"):
                fragment = snapshot.content[
                    import_node.start_byte : import_node.end_byte
                ].decode("utf-8")
                normalized = _normalize_java_import(fragment, module_name, snapshot)
                if normalized:
                    imports.append(normalized)

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
            if body:
                for child in body.children:
                    self._walk(child, snapshot, module_name, result, class_stack)
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
            # Nested callables (e.g., lambdas) are treated as implementation
            # detail, but their calls should be attributed to the enclosing
            # method for higher recall.
            calls = collect_call_identifiers(
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
            )
            if calls:
                result.call_records.append(
                    CallRecord(
                        qualified_name=qualified,
                        node_type=node_type,
                        callee_identifiers=list(calls),
                    )
                )
            return

        for child in getattr(node, "children", []):
            self._walk(child, snapshot, module_name, result, class_stack)


def module_name(repo_root: Path, snapshot: FileSnapshot) -> str:
    return module_name_from_path(
        repo_root,
        snapshot.record.relative_path,
        strip_suffix=True,
        treat_init_as_package=False,
    )


def _normalize_java_import(
    fragment: str, module_name: str, snapshot: FileSnapshot
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
        text = text[:-2]
        return text.strip() or None
    text = text.strip()
    if not text:
        return None
    repo_root = _repo_root_from_snapshot(snapshot)
    repo_prefix = runtime_paths.repo_name_prefix(repo_root)
    if repo_prefix and (text == repo_prefix or text.startswith(f"{repo_prefix}.")):
        return text
    top_package = _top_level_package(module_name, repo_prefix)
    if top_package and (text == top_package or text.startswith(f"{top_package}.")):
        return f"{repo_prefix}.{text}" if repo_prefix else text
    return text


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


def _extract_package_name(root, content: bytes) -> Optional[str]:
    for node in find_nodes_of_type(root, "package_declaration"):
        fragment = content[node.start_byte : node.end_byte].decode("utf-8").strip()
        if not fragment.startswith("package"):
            continue
        fragment = fragment[len("package") :].strip()
        if fragment.endswith(";"):
            fragment = fragment[:-1].strip()
        return fragment or None
    return None
