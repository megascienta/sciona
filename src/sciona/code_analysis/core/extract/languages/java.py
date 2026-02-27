# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Java Tree-sitter analyzer."""

from __future__ import annotations

from pathlib import Path

from ...module_naming import module_name_from_path
from ...normalize.model import (
    AnalysisResult,
    CallRecord,
    EdgeRecord,
    FileSnapshot,
    SemanticNodeRecord,
)
from ..analyzer import ASTAnalyzer
from ..utils import bootstrap_tree_sitter_parser, count_lines
from .java_calls import callee_text, resolve_java_calls
from .java_imports import (
    collect_java_import_model,
    extract_package,
    module_prefix_for_package,
)
from .java_nodes import JavaNodeState, walk_java_nodes
from .java_resolution import (
    collect_constructor_field_types,
    collect_declared_vars,
    collect_local_var_types,
    qualify_java_type,
)
from .query_surface import JAVA_CALL_NODE_TYPES, JAVA_SKIP_CALL_NODE_TYPES
from .analyzer_support import (
    assert_scope_resolver_parity,
    collect_targets_by_callable,
    emit_local_inheritance_edges,
    scope_resolver_from_pending_calls,
)


class JavaAnalyzer(ASTAnalyzer):
    language = "java"

    def __init__(self) -> None:
        self._parser, _language, diagnostics = bootstrap_tree_sitter_parser("java")
        self._parser_bootstrap_diagnostics = diagnostics

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
                    collect_constructor_field_types=collect_constructor_field_types,
                )

            emit_local_inheritance_edges(language=self.language, result=result)
            import_model = collect_java_import_model(
                root,
                snapshot.content,
                module_name,
                snapshot,
                module_prefix=module_prefix,
                module_index=getattr(self, "module_index", None),
            )
            imports = import_model.modules
            import_aliases = import_model.import_aliases
            member_aliases = import_model.member_aliases
            static_wildcard_targets = import_model.static_wildcard_targets

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
            outcome_diagnostics: dict[str, int] = {}
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
                    outcome_diagnostics=outcome_diagnostics,
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
                "imports_seen": import_model.imports_seen,
                "imports_internal": len(set(imports)),
                "import_aliases": len(import_aliases),
                "member_aliases": len(member_aliases),
                "static_wildcard_targets": len(static_wildcard_targets),
                "call_targets": total_call_targets,
                "resolved_call_targets": resolved_call_targets,
                "unresolved_call_targets": max(0, total_call_targets - resolved_call_targets),
                "call_resolution_outcomes": dict(sorted(outcome_diagnostics.items())),
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
