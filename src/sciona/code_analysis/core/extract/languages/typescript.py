# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""TypeScript Tree-sitter analyzer."""

from __future__ import annotations

import os
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
from .scope_resolver import ScopeResolver


SCOPE_RESOLVER_STRICT_COMPARE_ENV = "SCIONA_SCOPE_RESOLVER_STRICT_COMPARE"


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
            scope_resolver = _scope_resolver_from_pending_calls(state.pending_calls)
            for qualified, node_type, body_node, class_name in state.pending_calls:
                call_targets = collect_call_targets(
                    body_node,
                    snapshot.content,
                    call_node_types={"call_expression"},
                    skip_node_types={
                        "class_declaration",
                        "abstract_class_declaration",
                        "class",
                        "class_expression",
                    },
                    query_language=self.language,
                )
                if _scope_resolver_strict_compare():
                    _assert_scope_resolver_parity(
                        scope_resolver=scope_resolver,
                        body_node=body_node,
                        call_targets=call_targets,
                        expected_callable=qualified,
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


__all__ = [
    "TypeScriptAnalyzer",
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
    scope_resolver: ScopeResolver,
    body_node,
    call_targets,
    expected_callable: str,
) -> None:
    for target in call_targets:
        if target.call_span is None:
            continue
        resolved = scope_resolver.enclosing_callable_for_span(
            root=body_node,
            call_span=target.call_span,
        )
        if resolved not in {None, expected_callable}:
            raise RuntimeError(
                "scope resolver mismatch: "
                f"expected={expected_callable}, resolved={resolved}"
            )
