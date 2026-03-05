# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Java Tree-sitter analyzer."""

from __future__ import annotations

from pathlib import Path

from ....core.module_naming import module_name_from_path
from ....core.normalize.model import (
    AnalysisResult,
    CallRecord,
    EdgeRecord,
    FileSnapshot,
    SemanticNodeRecord,
)
from ....core.extract.analyzer import ASTAnalyzer
from ....core.extract.ir.extraction_buffer import ExtractionBuffer
from ....core.extract.parsing.parser_bootstrap import bootstrap_tree_sitter_parser
from ....core.extract.parsing.query_helpers import count_lines, find_direct_children_query
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
from ...common.query_surface import JAVA_CALL_NODE_TYPES, JAVA_SKIP_CALL_NODE_TYPES
from ...common.analyzer_support import (
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
        buffer = ExtractionBuffer()
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
        )
        buffer.add_node(module_node)

        root = tree.root_node
        package_name = extract_package(root, snapshot.content)
        module_prefix = module_prefix_for_package(module_name, package_name)

        state = JavaNodeState()
        for child in find_direct_children_query(root, language_name=self.language):
            walk_java_nodes(
                child,
                language=self.language,
                snapshot=snapshot,
                module_name=module_name,
                result=buffer,
                state=state,
                collect_declared_vars=collect_declared_vars,
                collect_constructor_field_types=collect_constructor_field_types,
            )
        buffer.diagnostics["name_collisions_detected"] = (
            state.name_disambiguator.collisions_detected
        )
        buffer.diagnostics["name_collisions_disambiguated"] = (
            state.name_disambiguator.collisions_disambiguated
        )

        emit_local_inheritance_edges(language=self.language, result=buffer)
        import_model = collect_java_import_model(
            root,
            snapshot.content,
            module_name,
            snapshot,
            module_prefix=module_prefix,
            module_index=getattr(self, "module_index", None),
        )
        buffer.diagnostics["imports_seen"] = import_model.imports_seen
        buffer.diagnostics["imports_internal"] = import_model.imports_internal
        buffer.diagnostics["imports_filtered_not_internal"] = (
            import_model.imports_filtered_not_internal
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

        if resolved_calls:
            for _language, qualified, node_type, callee_identifiers in resolved_calls:
                buffer.add_call(
                    CallRecord(
                        qualified_name=qualified,
                        node_type=node_type,
                        callee_identifiers=callee_identifiers,
                    )
                )

        for module in sorted(set(imports)):
            buffer.add_edge(
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
        return buffer.finalize()

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
