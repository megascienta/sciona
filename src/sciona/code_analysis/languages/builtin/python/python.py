# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Python Tree-sitter analyzer."""

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
from ....core.extract.parsing.parse_validation import (
    collect_parse_validation_diagnostics,
)
from ....core.extract.parsing.query_helpers import (
    count_lines,
    find_direct_children_of_types_query,
)
from .python_calls import resolve_python_calls
from .python_imports import collect_python_import_model
from .python_nodes import PythonNodeState, walk_python_nodes
from ...common.ir import alias_maps_from_binding_facts
from ...common.query.query_surface import (
    PYTHON_CALL_NODE_TYPES,
    PYTHON_SKIP_CALL_NODE_TYPES,
    PYTHON_STRUCTURAL_CARRIER_NODE_TYPES,
    PYTHON_STRUCTURAL_NODE_TYPES,
)
from .python_resolution import (
    collect_callable_instance_map,
    collect_callable_local_bindings,
    collect_module_instance_map,
)
from .python_resolution import collect_class_instance_map
from ...common.support.analyzer_support import (
    assert_scope_resolver_parity,
    collect_targets_by_callable,
    emit_local_inheritance_edges,
    scope_resolver_from_pending_calls,
)


class PythonAnalyzer(ASTAnalyzer):
    language = "python"

    def __init__(self) -> None:
        super().__init__()
        self._parser, _language, diagnostics = bootstrap_tree_sitter_parser("python")
        self._parser_bootstrap_diagnostics = diagnostics

    def analyze(self, snapshot: FileSnapshot, module_name: str) -> AnalysisResult:
        tree = self._parser.parse(snapshot.content)
        buffer = ExtractionBuffer()
        parse_diagnostics = collect_parse_validation_diagnostics(
            tree, language_name=self.language
        )
        buffer.diagnostics.update(parse_diagnostics)
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
        state = PythonNodeState()
        for child in find_direct_children_of_types_query(
            root,
            language_name=self.language,
            node_types=tuple(
                sorted(PYTHON_STRUCTURAL_NODE_TYPES | PYTHON_STRUCTURAL_CARRIER_NODE_TYPES)
            ),
        ):
            walk_python_nodes(
                child,
                language=self.language,
                snapshot=snapshot,
                module_name=module_name,
                result=buffer,
                state=state,
            )
        buffer.diagnostics["name_collisions_detected"] = (
            state.name_disambiguator.collisions_detected
        )
        buffer.diagnostics["name_collisions_disambiguated"] = (
            state.name_disambiguator.collisions_disambiguated
        )
        emit_local_inheritance_edges(language=self.language, result=buffer)
        import_model = collect_python_import_model(
            root,
            snapshot,
            module_name,
            module_index=self.module_index,
        )
        buffer.diagnostics["imports_seen"] = import_model.imports_seen
        buffer.diagnostics["imports_internal"] = import_model.imports_internal
        buffer.diagnostics["imports_filtered_not_internal"] = (
            import_model.imports_filtered_not_internal
        )
        imports = import_model.modules
        import_aliases, member_aliases = alias_maps_from_binding_facts(
            import_model.local_binding_facts
        )
        raw_module_map = import_model.raw_module_map
        module_instance_map = collect_module_instance_map(
            root,
            snapshot,
            state.class_name_candidates,
            import_aliases,
            member_aliases,
            raw_module_map,
        )
        class_instance_maps = {
            class_name: collect_class_instance_map(
                class_body,
                snapshot,
                state.class_name_candidates,
                import_aliases,
                member_aliases,
                raw_module_map,
            )
            for class_name, class_body in state.class_body_map.items()
        }
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
            call_node_types=set(PYTHON_CALL_NODE_TYPES),
            skip_node_types=set(PYTHON_SKIP_CALL_NODE_TYPES),
        )
        assert_scope_resolver_parity(
            pending_callables=set(pending_by_qualified),
            call_targets_by_callable=call_targets_by_callable,
        )
        for qualified, (node_type, body_node, class_name) in pending_by_qualified.items():
            local_instance_map = dict(module_instance_map)
            if class_name:
                local_instance_map.update(class_instance_maps.get(class_name, {}))
            local_instance_map.update(
                collect_callable_instance_map(
                    body_node,
                    snapshot,
                    state.class_name_candidates,
                    import_aliases,
                    member_aliases,
                    raw_module_map,
                )
            )
            local_binding_names = collect_callable_local_bindings(body_node, snapshot)
            call_targets = call_targets_by_callable.get(qualified, ())
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
                state.class_name_candidates,
                local_binding_names,
                import_model.local_binding_facts,
            )
            if resolved:
                buffer.add_call(
                    CallRecord(
                        qualified_name=qualified,
                        node_type=node_type,
                        callee_identifiers=list(resolved),
                        local_binding_facts=list(import_model.local_binding_facts),
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
        treat_init_as_package=True,
    )


__all__ = ["PythonAnalyzer", "module_name"]
