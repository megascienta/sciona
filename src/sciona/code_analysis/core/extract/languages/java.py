# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Java Tree-sitter analyzer."""

from __future__ import annotations

import os
from pathlib import Path
from collections import defaultdict
from typing import List

from ....tools.call_extraction import (
    collect_call_targets,
)
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
from ..utils import count_lines, find_nodes_of_types_query
from .java_calls import callee_text, resolve_java_calls
from .java_imports import (
    extract_package,
    import_simple_name_node,
    module_prefix_for_package,
    normalize_import_node,
)
from .java_nodes import JavaNodeState, walk_java_nodes
from .java_resolution import (
    collect_declared_vars,
    collect_local_var_types,
    qualify_java_type,
)
from .scope_resolver import ScopeResolver
from .shared import is_internal_module

SCOPE_RESOLVER_STRICT_COMPARE_ENV = "SCIONA_SCOPE_RESOLVER_STRICT_COMPARE"

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
            import_class_map: dict[str, str] = {}
            for import_node in find_nodes_of_types_query(
                root,
                language_name="java",
                node_types=("import_declaration",),
            ):
                normalized = normalize_import_node(
                    import_node,
                    snapshot.content,
                    module_name,
                    snapshot,
                    module_prefix=module_prefix,
                )
                if not normalized:
                    continue
                if not is_internal_module(normalized, getattr(self, "module_index", None)):
                    continue
                imports.append(normalized)
                simple_name = import_simple_name_node(import_node, snapshot.content)
                if simple_name:
                    import_class_map[simple_name] = normalized

            resolved_calls: list[tuple[str, str, str, list[str]]] = []
            scope_resolver = _scope_resolver_from_pending_calls(state.pending_calls)
            pending_by_qualified = {
                qualified: (node_type, body_node, class_name)
                for qualified, node_type, body_node, class_name in state.pending_calls
            }
            call_targets_by_callable = _collect_targets_by_callable(
                scope_resolver=scope_resolver,
                pending_calls=state.pending_calls,
                snapshot=snapshot,
                language=self.language,
            )
            if _scope_resolver_strict_compare():
                _assert_scope_resolver_parity(
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
                    import_class_map,
                    class_name,
                    instance_types,
                    module_prefix,
                    qualify_java_type,
                )
                if resolved:
                    resolved_calls.append((self.language, qualified, node_type, list(resolved)))

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
    "JavaAnalyzer",
    "module_name",
]


def _scope_resolver_strict_compare() -> bool:
    value = os.getenv(SCOPE_RESOLVER_STRICT_COMPARE_ENV, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _scope_resolver_from_pending_calls(
    pending_calls: list[tuple[str, str, object | None, str | None]],
) -> ScopeResolver:
    spans: dict[tuple[int, int], str] = {}
    for qualified, _node_type, body_node, _class_name in pending_calls:
        callable_node = getattr(body_node, "parent", None)
        if callable_node is None:
            continue
        spans[(callable_node.start_byte, callable_node.end_byte)] = qualified
    return ScopeResolver(callable_qname_by_span=spans)


def _assert_scope_resolver_parity(
    *,
    pending_callables: set[str],
    call_targets_by_callable: dict[str, tuple[object, ...]],
) -> None:
    unknown = set(call_targets_by_callable) - pending_callables
    if unknown:
        raise RuntimeError(f"scope resolver mismatch: unknown callables {sorted(unknown)}")


def _collect_targets_by_callable(
    *,
    scope_resolver: ScopeResolver,
    pending_calls: list[tuple[str, str, object | None, str | None]],
    snapshot: FileSnapshot,
    language: str,
) -> dict[str, tuple[object, ...]]:
    grouped: dict[str, list[object]] = defaultdict(list)
    for _qualified, _node_type, body_node, _class_name in pending_calls:
        if body_node is None:
            continue
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
            callee_renderer=callee_text,
            query_language=language,
        )
        for target in call_targets:
            if target.call_span is None:
                continue
            caller = scope_resolver.enclosing_callable_for_span(
                root=body_node,
                call_span=target.call_span,
            )
            if caller is None:
                continue
            grouped[caller].append(target)
    return {qualified: tuple(targets) for qualified, targets in grouped.items()}
