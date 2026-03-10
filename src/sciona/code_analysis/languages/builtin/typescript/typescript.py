# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""TypeScript Tree-sitter analyzer."""

from __future__ import annotations

from pathlib import Path

from ....core.module_naming import module_name_from_path
from ....core.normalize_model import (
    AnalysisResult,
    CallRecord,
    EdgeRecord,
    FileSnapshot,
    SemanticNodeRecord,
)
from ....core.extract.analyzer import ASTAnalyzer
from ....core.extract.ir.extraction_buffer import ExtractionBuffer
from ....core.extract.parsing.parser_bootstrap import bootstrap_tree_sitter_parser
from ....core.extract.parsing.query_helpers import (
    count_lines,
    find_direct_children_of_types_query,
)
from .typescript_calls import callee_text, resolve_typescript_calls
from .typescript_imports import collect_typescript_import_model
from .typescript_nodes import TypeScriptNodeState, walk_typescript_nodes
from ...common.query.query_surface import (
    TYPESCRIPT_CALL_NODE_TYPES,
    TYPESCRIPT_SKIP_CALL_NODE_TYPES,
    TYPESCRIPT_STRUCTURAL_CARRIER_NODE_TYPES,
    TYPESCRIPT_STRUCTURAL_NODE_TYPES,
)
from .typescript_resolution import (
    collect_callable_typed_binding_instance_map,
    resolve_pending_instances,
)
from ...common.support.analyzer_support import (
    assert_scope_resolver_parity,
    collect_targets_by_callable,
    emit_local_inheritance_edges,
    scope_resolver_from_pending_calls,
)


class TypeScriptAnalyzer(ASTAnalyzer):
    language = "typescript"

    def __init__(self) -> None:
        self._parser, _language, diagnostics = bootstrap_tree_sitter_parser("typescript")
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
        state = TypeScriptNodeState()
        for child in find_direct_children_of_types_query(
            root,
            language_name=self.language,
            node_types=tuple(
                sorted(
                    TYPESCRIPT_STRUCTURAL_NODE_TYPES
                    | TYPESCRIPT_STRUCTURAL_CARRIER_NODE_TYPES
                )
            ),
        ):
            walk_typescript_nodes(
                child,
                language=self.language,
                snapshot=snapshot,
                module_name=module_name,
                result=buffer,
                state=state,
                function_depth=0,
            )
        buffer.diagnostics["name_collisions_detected"] = (
            state.name_disambiguator.collisions_detected
        )
        buffer.diagnostics["name_collisions_disambiguated"] = (
            state.name_disambiguator.collisions_disambiguated
        )
        emit_local_inheritance_edges(language=self.language, result=buffer)
        import_model = collect_typescript_import_model(
            root,
            snapshot,
            module_name,
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
            call_node_types=set(TYPESCRIPT_CALL_NODE_TYPES),
            skip_node_types=set(TYPESCRIPT_SKIP_CALL_NODE_TYPES),
            callee_field_names=("function", "constructor", "type"),
            callee_renderer=callee_text,
        )
        assert_scope_resolver_parity(
            pending_callables=set(pending_by_qualified),
            call_targets_by_callable=call_targets_by_callable,
        )
        for qualified, (node_type, body_node, class_name) in pending_by_qualified.items():
            call_targets = call_targets_by_callable.get(qualified, ())
            callable_instance_map = collect_callable_typed_binding_instance_map(
                body_node,
                content=snapshot.content,
                class_name_candidates=state.class_name_candidates,
                import_aliases=import_aliases,
                member_aliases=member_aliases,
            )
            effective_instance_map = {
                **state.instance_map,
                **callable_instance_map,
            }
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
                effective_instance_map,
                state.class_instance_map,
            )
            if resolved:
                buffer.add_call(
                    CallRecord(
                        qualified_name=qualified,
                        node_type=node_type,
                        callee_identifiers=list(resolved),
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
    raw = module_name_from_path(
        repo_root,
        snapshot.record.relative_path,
        strip_suffix=False,
        treat_init_as_package=False,
    )
    return _normalize_typescript_module_name(raw)


def _normalize_typescript_module_name(module_name: str) -> str:
    if module_name.endswith(".d.ts"):
        return module_name[: -len(".d.ts")]
    if module_name.endswith(".tsx"):
        return module_name[: -len(".tsx")]
    if module_name.endswith(".ts"):
        return module_name[: -len(".ts")]
    if module_name.endswith(".mjs"):
        return module_name[: -len(".mjs")]
    if module_name.endswith(".cjs"):
        return module_name[: -len(".cjs")]
    if module_name.endswith(".js"):
        return module_name[: -len(".js")]
    return module_name


__all__ = ["TypeScriptAnalyzer", "module_name"]
