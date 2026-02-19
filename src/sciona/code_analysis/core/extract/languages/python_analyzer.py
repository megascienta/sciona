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
from .python_imports import (
    _python_module_name,
    _repo_root_from_snapshot,
    _resolved_python_imports,
)

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
            root = tree.root_node
            for child in root.children:
                self._walk_node(
                    node=child,
                    snapshot=snapshot,
                    module_name=module_name,
                    result=result,
                    class_stack=class_stack,
                )

            is_package = snapshot.record.path.name == "__init__.py"

            # Extract imports (best-effort syntax parsing; not full resolution).
            imports: List[str] = []
            repo_root = _repo_root_from_snapshot(snapshot)
            repo_prefix = runtime_paths.repo_name_prefix(repo_root)
            local_packages = set(runtime_packaging.local_package_names(repo_root))
            for child in root.children:
                if child.type in {"import_statement", "import_from_statement"}:
                    segment = snapshot.content[
                        child.start_byte : child.end_byte
                    ].decode("utf-8")
                    imports.extend(
                        _resolved_python_imports(
                            segment,
                            module_name,
                            is_package,
                            repo_prefix=repo_prefix,
                            local_packages=local_packages,
                        )
                    )

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
        return _python_module_name(repo_root, snapshot)

    def _walk_node(
        self,
        node,
        snapshot: FileSnapshot,
        module_name: str,
        result: AnalysisResult,
        class_stack: List[str],
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
            class_stack.append(qualified)
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    self._walk_node(child, snapshot, module_name, result, class_stack)
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
            else:
                node_type = "function"
                parent = module_name
                parent_node_type = "module"
                qualified = f"{module_name}.{func_name}"
                edge_type = "CONTAINS"
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
            # Nested callables are treated as implementation detail, not structural
            # nodes, but we still want their calls attributed to the enclosing
            # callable for higher recall.
            calls = collect_call_identifiers(
                body,
                snapshot.content,
                call_node_types={"call"},
                skip_node_types={"class_definition"},
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

        # Continue traversal for other nodes to find nested definitions
        for child in getattr(node, "children", []):
            self._walk_node(child, snapshot, module_name, result, class_stack)
