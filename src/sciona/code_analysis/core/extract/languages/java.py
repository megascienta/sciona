# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Java Tree-sitter analyzer."""

from __future__ import annotations

from pathlib import Path
from typing import List

from tree_sitter import Parser
from tree_sitter_languages import get_language

from ...module_naming import module_name_from_path
from ...normalize.model import (
    AnalysisResult,
    CallRecord,
    EdgeRecord,
    FileSnapshot,
    SemanticNodeRecord,
)
from ..analyzer import ASTAnalyzer
from ..utils import count_lines, find_nodes_of_types_query
from .java_calls import callee_text, resolve_java_calls
from .java_imports import (
    collect_java_import_bindings,
    extract_package,
    module_prefix_for_package,
)
from .java_nodes import JavaNodeState, walk_java_nodes
from .java_resolution import (
    collect_declared_vars,
    collect_local_var_types,
    qualify_java_type,
)
from .query_surface import (
    JAVA_CALL_NODE_TYPES,
    JAVA_IMPORT_NODE_TYPES,
    JAVA_SKIP_CALL_NODE_TYPES,
)
from .analyzer_support import (
    assert_scope_resolver_parity,
    collect_targets_by_callable,
    scope_resolver_from_pending_calls,
)
from .shared import is_internal_module

class JavaAnalyzer(ASTAnalyzer):
    language = "java"

    def __init__(self) -> None:
        self._parser = Parser()
        language = get_language("java")
        if hasattr(self._parser, "set_language"):
            self._parser.set_language(language)
        else:
            self._parser.language = language

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
            root = tree.root_node
            package_name = extract_package(root, snapshot.content)
            module_prefix = module_prefix_for_package(module_name, package_name)
            if package_name:
                if module_metadata is None:
                    module_metadata = {"package": package_name}
                else:
                    module_metadata["package"] = package_name
                module_node.metadata = module_metadata

            state = JavaNodeState()
            for child in root.children:
                walk_java_nodes(
                    child,
                    language=self.language,
                    snapshot=snapshot,
                    module_name=module_name,
                    result=result,
                    state=state,
                    collect_declared_vars=collect_declared_vars,
                )

            imports: List[str] = []
            import_aliases: dict[str, str] = {}
            member_aliases: dict[str, str] = {}
            static_wildcard_targets: set[str] = set()
            imports_seen = 0
            for import_node in find_nodes_of_types_query(
                root,
                language_name="java",
                node_types=JAVA_IMPORT_NODE_TYPES,
            ):
                imports_seen += 1
                bindings = collect_java_import_bindings(
                    import_node,
                    snapshot.content,
                    module_name,
                    snapshot,
                    module_prefix=module_prefix,
                )
                if bindings is None:
                    continue
                normalized = bindings.normalized_module
                if not is_internal_module(normalized, getattr(self, "module_index", None)):
                    continue
                imports.append(normalized)
                for alias, target in bindings.import_aliases:
                    if alias and target:
                        import_aliases.setdefault(alias, target)
                for alias, target in bindings.member_aliases:
                    if alias and target:
                        member_aliases.setdefault(alias, target)
                for target in bindings.static_wildcard_targets:
                    if target:
                        static_wildcard_targets.add(target)

            resolved_calls: list[tuple[str, str, str, list[str]]] = []
            scope_resolver = scope_resolver_from_pending_calls(state.pending_calls)
            pending_by_qualified = {
                qualified: (node_type, body_node, class_name)
                for qualified, node_type, body_node, class_name in state.pending_calls
            }
            call_targets_by_callable = collect_targets_by_callable(
                scope_resolver=scope_resolver,
                pending_calls=state.pending_calls,
                snapshot=snapshot,
                language=self.language,
                call_node_types=set(JAVA_CALL_NODE_TYPES),
                skip_node_types=set(JAVA_SKIP_CALL_NODE_TYPES),
                callee_field_names=("name", "type", "function"),
                callee_renderer=callee_text,
            )
            assert_scope_resolver_parity(
                pending_callables=set(pending_by_qualified),
                call_targets_by_callable=call_targets_by_callable,
            )
            total_call_targets = sum(len(targets) for targets in call_targets_by_callable.values())
            resolved_call_targets = 0
            for qualified, (node_type, body_node, class_name) in pending_by_qualified.items():
                local_types = collect_local_var_types(body_node, snapshot)
                instance_types = {}
                if class_name and state.class_field_types.get(class_name):
                    instance_types.update(state.class_field_types[class_name])
                instance_types.update(local_types)
                call_targets = call_targets_by_callable.get(qualified, ())
                resolved = resolve_java_calls(
                    call_targets,
                    module_name,
                    state.module_functions,
                    state.class_methods,
                    state.class_name_map,
                    state.class_name_candidates,
                    import_aliases,
                    member_aliases,
                    static_wildcard_targets,
                    class_name,
                    instance_types,
                    module_prefix,
                    qualify_java_type,
                )
                if resolved:
                    resolved_calls.append((self.language, qualified, node_type, list(resolved)))
                    resolved_call_targets += len(resolved)

            if resolved_calls:
                for _language, qualified, node_type, callee_identifiers in resolved_calls:
                    result.call_records.append(
                        CallRecord(
                            qualified_name=qualified,
                            node_type=node_type,
                            callee_identifiers=callee_identifiers,
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
            diagnostics = {
                "imports_seen": imports_seen,
                "imports_internal": len(set(imports)),
                "import_aliases": len(import_aliases),
                "member_aliases": len(member_aliases),
                "static_wildcard_targets": len(static_wildcard_targets),
                "call_targets": total_call_targets,
                "resolved_call_targets": resolved_call_targets,
                "unresolved_call_targets": max(0, total_call_targets - resolved_call_targets),
            }
            metadata = dict(module_node.metadata or {})
            metadata["resolution_diagnostics"] = diagnostics
            module_node.metadata = metadata
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


__all__ = ["JavaAnalyzer", "module_name"]
