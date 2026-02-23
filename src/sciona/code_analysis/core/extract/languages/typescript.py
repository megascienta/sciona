# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""TypeScript Tree-sitter analyzer."""

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
from .typescript_calls import resolve_typescript_calls
from .typescript_imports import collect_typescript_imports
from .typescript_nodes import TypeScriptNodeState, walk_typescript_nodes
from .typescript_resolution import resolve_pending_instances


class TypeScriptAnalyzer(ASTAnalyzer):
    language = "typescript"

    def __init__(self) -> None:
        self._parser = build_parser("typescript")

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
            state = TypeScriptNodeState()
            for child in root.children:
                walk_typescript_nodes(
                    child,
                    language=self.language,
                    snapshot=snapshot,
                    module_name=module_name,
                    result=result,
                    state=state,
                    function_depth=0,
                )
            imports, import_aliases, member_aliases = collect_typescript_imports(
                root,
                snapshot,
                module_name,
                module_index=getattr(self, "module_index", None),
            )
            resolve_pending_instances(
                state.pending_instance_assignments,
                state.pending_class_instances,
                state.pending_alias_assignments,
                state.pending_class_aliases,
                state.instance_map,
                state.class_instance_map,
                state.class_name_candidates,
                state.class_name_map,
                import_aliases,
                member_aliases,
            )
            for qualified, node_type, body_node, class_name in state.pending_calls:
                call_targets = collect_call_targets(
                    body_node,
                    snapshot.content,
                    call_node_types={"call_expression"},
                    skip_node_types={"class_declaration"},
                )
                resolved = resolve_typescript_calls(
                    call_targets,
                    module_name,
                    state.module_functions,
                    state.class_methods,
                    class_name,
                    import_aliases,
                    member_aliases,
                    state.class_name_map,
                    state.class_name_candidates,
                    state.instance_map,
                    state.class_instance_map,
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
        treat_init_as_package=False,
    )


__all__ = [
    "TypeScriptAnalyzer",
    "module_name",
]
