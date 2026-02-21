# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Python Tree-sitter analyzer."""

from __future__ import annotations

from pathlib import Path

from ....tools.call_extraction import collect_call_targets
from ....tools.tree_sitter import build_parser
from ...module_naming import module_name_from_path
from ...normalize.model import (
    AnalysisResult,
    CallRecord,
    EdgeRecord,
    FileSnapshot,
    SemanticNodeRecord,
)
from ..analyzer import ASTAnalyzer
from ..utils import count_lines
from .python_calls import resolve_python_calls
from .python_imports import collect_python_imports
from .python_nodes import PythonNodeState, walk_python_nodes
from .python_resolution import collect_callable_instance_map, collect_module_instance_map


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
            root = tree.root_node
            state = PythonNodeState()
            for child in root.children:
                walk_python_nodes(
                    child,
                    language=self.language,
                    snapshot=snapshot,
                    module_name=module_name,
                    result=result,
                    state=state,
                )
            imports, import_aliases, member_aliases, raw_module_map = collect_python_imports(
                root,
                snapshot,
                module_name,
                module_index=getattr(self, "module_index", None),
            )
            module_instance_map = collect_module_instance_map(
                root,
                snapshot,
                state.class_name_map,
                import_aliases,
                member_aliases,
                raw_module_map,
            )
            for qualified, node_type, body_node, class_name in state.pending_calls:
                local_instance_map = dict(module_instance_map)
                local_instance_map.update(
                    collect_callable_instance_map(
                        body_node,
                        snapshot,
                        state.class_name_map,
                        import_aliases,
                        member_aliases,
                        raw_module_map,
                    )
                )
                call_targets = collect_call_targets(
                    body_node,
                    snapshot.content,
                    call_node_types={"call"},
                    skip_node_types={"class_definition"},
                )
                resolved = resolve_python_calls(
                    call_targets,
                    module_name,
                    state.module_functions,
                    state.class_methods,
                    class_name,
                    import_aliases,
                    member_aliases,
                    raw_module_map,
                    local_instance_map,
                )
                if resolved:
                    result.call_records.append(
                        CallRecord(
                            qualified_name=qualified,
                            node_type=node_type,
                            callee_identifiers=list(resolved),
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
        return module_name(repo_root, snapshot)


def module_name(repo_root: Path, snapshot: FileSnapshot) -> str:
    return module_name_from_path(
        repo_root,
        snapshot.record.relative_path,
        strip_suffix=True,
        treat_init_as_package=True,
    )


__all__ = [
    "PythonAnalyzer",
    "module_name",
]
