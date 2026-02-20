# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""TypeScript Tree-sitter analyzer."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import List, Optional

from ....tools.tree_sitter import build_parser

from ...module_naming import module_name_from_path
from ....tools.call_extraction import CallTarget, collect_call_targets
from ...normalize.model import (
    AnalysisResult,
    CallRecord,
    EdgeRecord,
    FileSnapshot,
    SemanticNodeRecord,
)
from ..analyzer import ASTAnalyzer
from ..utils import count_lines, find_nodes_of_type
from .....runtime import paths as runtime_paths


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
            class_stack: List[str] = []
            module_functions: set[str] = set()
            class_methods: dict[str, set[str]] = {}
            pending_calls: list[tuple[str, str, object | None, str | None]] = []
            root = tree.root_node
            for child in root.children:
                self._walk(
                    child,
                    snapshot,
                    module_name,
                    result,
                    class_stack,
                    module_functions,
                    class_methods,
                    pending_calls,
                    function_depth=0,
                )
            (
                imports,
                import_aliases,
                member_aliases,
            ) = _collect_imports(
                root,
                snapshot,
                module_name,
                module_index=getattr(self, "module_index", None),
            )
            for qualified, node_type, body_node, class_name in pending_calls:
                call_targets = collect_call_targets(
                    body_node,
                    snapshot.content,
                    call_node_types={"call_expression"},
                    skip_node_types={
                        "class_declaration",
                    },
                )
                resolved = _resolve_typescript_calls(
                    call_targets,
                    module_name,
                    module_functions,
                    class_methods,
                    class_name,
                    import_aliases,
                    member_aliases,
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
        return module_name_from_path(
            repo_root,
            snapshot.record.relative_path,
            strip_suffix=True,
            treat_init_as_package=False,
        )

    def _walk(
        self,
        node,
        snapshot: FileSnapshot,
        module_name: str,
        result: AnalysisResult,
        class_stack: List[str],
        module_functions: set[str],
        class_methods: dict[str, set[str]],
        pending_calls: list[tuple[str, str, object | None, str | None]],
        function_depth: int,
    ) -> None:
        if node.type == "class_declaration":
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
            body = node.child_by_field_name("body")
            class_stack.append(qualified)
            class_methods.setdefault(qualified, set())
            if body:
                for child in body.children:
                    self._walk(
                        child,
                        snapshot,
                        module_name,
                        result,
                        class_stack,
                        module_functions,
                        class_methods,
                        pending_calls,
                        function_depth=function_depth,
                    )
            class_stack.pop()
            return

        # v1 extraction: declarations only (function_declaration, class_declaration, method_definition).
        if node.type in {"function_declaration", "method_definition"}:
            name_node = node.child_by_field_name("name")
            if not name_node:
                return
            func_name = snapshot.content[
                name_node.start_byte : name_node.end_byte
            ].decode("utf-8")
            if node.type == "method_definition":
                if not class_stack:
                    # Ignore object-literal methods; only class members are structural methods.
                    return
                node_type = "method"
                parent = class_stack[-1]
                parent_node_type = "class"
                qualified = f"{parent}.{func_name}"
                edge_type = "DEFINES_METHOD"
                class_methods.setdefault(parent, set()).add(func_name)
            else:
                node_type = "function"
                parent = module_name
                parent_node_type = "module"
                qualified = f"{module_name}.{func_name}"
                edge_type = "CONTAINS"
                module_functions.add(func_name)
            result.nodes.append(
                SemanticNodeRecord(
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
            )
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
            body_node = node.child_by_field_name("body")
            pending_calls.append(
                (
                    qualified,
                    node_type,
                    body_node,
                    class_stack[-1] if class_stack else None,
                )
            )
            self._walk_children(
                node,
                snapshot,
                module_name,
                result,
                class_stack,
                module_functions,
                class_methods,
                pending_calls,
                function_depth=function_depth + 1,
            )
            return

        if node.type == "variable_declarator" and not class_stack and function_depth == 0:
            name_node = node.child_by_field_name("name")
            value_node = node.child_by_field_name("value") or node.child_by_field_name(
                "initializer"
            )
            if not name_node or not value_node:
                return
            if value_node.type not in {"arrow_function", "function", "function_expression"}:
                return
            if name_node.type != "identifier":
                return
            func_name = snapshot.content[
                name_node.start_byte : name_node.end_byte
            ].decode("utf-8")
            qualified = f"{module_name}.{func_name}"
            module_functions.add(func_name)
            result.nodes.append(
                SemanticNodeRecord(
                    language=self.language,
                    node_type="function",
                    qualified_name=qualified,
                    display_name=func_name,
                    file_path=snapshot.record.relative_path,
                    start_line=value_node.start_point[0] + 1,
                    end_line=value_node.end_point[0] + 1,
                    start_byte=value_node.start_byte,
                    end_byte=value_node.end_byte,
                )
            )
            result.edges.append(
                EdgeRecord(
                    src_language=self.language,
                    src_node_type="module",
                    src_qualified_name=module_name,
                    dst_language=self.language,
                    dst_node_type="function",
                    dst_qualified_name=qualified,
                    edge_type="CONTAINS",
                )
            )
            body_node = _function_body_node(value_node)
            pending_calls.append(
                (
                    qualified,
                    "function",
                    body_node,
                    None,
                )
            )
            return

        if node.type in {
            "public_field_definition",
            "private_field_definition",
            "property_definition",
            "field_definition",
        } and class_stack:
            name_node = node.child_by_field_name("name")
            value_node = node.child_by_field_name("value") or node.child_by_field_name(
                "initializer"
            )
            if not name_node or not value_node:
                return
            if value_node.type not in {"arrow_function", "function", "function_expression"}:
                return
            if name_node.type != "property_identifier":
                return
            func_name = snapshot.content[
                name_node.start_byte : name_node.end_byte
            ].decode("utf-8")
            parent = class_stack[-1]
            qualified = f"{parent}.{func_name}"
            class_methods.setdefault(parent, set()).add(func_name)
            result.nodes.append(
                SemanticNodeRecord(
                    language=self.language,
                    node_type="method",
                    qualified_name=qualified,
                    display_name=func_name,
                    file_path=snapshot.record.relative_path,
                    start_line=value_node.start_point[0] + 1,
                    end_line=value_node.end_point[0] + 1,
                    start_byte=value_node.start_byte,
                    end_byte=value_node.end_byte,
                )
            )
            result.edges.append(
                EdgeRecord(
                    src_language=self.language,
                    src_node_type="class",
                    src_qualified_name=parent,
                    dst_language=self.language,
                    dst_node_type="method",
                    dst_qualified_name=qualified,
                    edge_type="DEFINES_METHOD",
                )
            )
            body_node = _function_body_node(value_node)
            pending_calls.append(
                (
                    qualified,
                    "method",
                    body_node,
                    parent,
                )
            )
            return

        self._walk_children(
            node,
            snapshot,
            module_name,
            result,
            class_stack,
            module_functions,
            class_methods,
            pending_calls,
            function_depth=function_depth,
        )

    def _walk_children(
        self,
        node,
        snapshot: FileSnapshot,
        module_name: str,
        result: AnalysisResult,
        class_stack: List[str],
        module_functions: set[str],
        class_methods: dict[str, set[str]],
        pending_calls: list[tuple[str, str, object | None, str | None]],
        *,
        function_depth: int,
    ) -> None:
        next_depth = function_depth + 1 if node.type in {
            "function",
            "function_expression",
            "arrow_function",
            "method_definition",
            "function_declaration",
        } else function_depth
        for child in getattr(node, "children", []):
            self._walk(
                child,
                snapshot,
                module_name,
                result,
                class_stack,
                module_functions,
                class_methods,
                pending_calls,
                function_depth=next_depth,
            )


def _resolve_typescript_calls(
    targets: List[CallTarget],
    module_name: str,
    module_functions: set[str],
    class_methods: dict[str, set[str]],
    class_name: str | None,
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
) -> List[str]:
    resolved: list[str] = []
    class_method_names = class_methods.get(class_name, set()) if class_name else set()
    for target in targets:
        terminal = target.terminal
        callee_text = (target.callee_text or "").strip()
        if "." in callee_text:
            head, rest = callee_text.split(".", 1)
            if head in import_aliases:
                resolved.append(f"{import_aliases[head]}.{rest}")
                continue
        if terminal in member_aliases:
            resolved.append(member_aliases[terminal])
            continue
        if class_name and _is_receiver_call(callee_text) and terminal in class_method_names:
            resolved.append(f"{class_name}.{terminal}")
            continue
        if _is_unqualified(callee_text) and terminal in module_functions:
            resolved.append(f"{module_name}.{terminal}")
            continue
        resolved.append(terminal)
    return resolved


def _is_unqualified(callee_text: str) -> bool:
    return "." not in callee_text


def _is_receiver_call(callee_text: str) -> bool:
    return callee_text.startswith("this.") or callee_text.startswith("super.")


def _function_body_node(node) -> object | None:
    if node is None:
        return None
    return node.child_by_field_name("body") or node


def _is_internal_module(
    module_name: str, repo_prefix: str, module_index: set[str] | None
) -> bool:
    if module_index is not None:
        return module_name in module_index
    if not repo_prefix:
        return True
    return module_name == repo_prefix or module_name.startswith(f"{repo_prefix}.")


def module_name(repo_root: Path, snapshot: FileSnapshot) -> str:
    return module_name_from_path(
        repo_root,
        snapshot.record.relative_path,
        strip_suffix=True,
        treat_init_as_package=False,
    )


def _collect_imports(
    root,
    snapshot: FileSnapshot,
    module_name: str,
    *,
    module_index: set[str] | None,
) -> tuple[list[str], dict[str, str], dict[str, str]]:
    imports: list[str] = []
    import_aliases: dict[str, str] = {}
    member_aliases: dict[str, str] = {}
    repo_prefix = runtime_paths.repo_name_prefix(_repo_root_from_snapshot(snapshot))
    nodes = list(find_nodes_of_type(root, "import_statement"))
    nodes.extend(list(find_nodes_of_type(root, "export_statement")))
    nodes.extend(list(find_nodes_of_type(root, "import_equals_declaration")))
    for node in nodes:
        fragment = snapshot.content[node.start_byte : node.end_byte].decode("utf-8")
        module_spec = _extract_module_spec(fragment)
        if not module_spec:
            continue
        normalized = _normalize_import(module_spec, snapshot, module_name)
        if not normalized or not _is_internal_module(
            normalized, repo_prefix, module_index
        ):
            continue
        imports.append(normalized)
        _populate_ts_aliases(fragment, normalized, import_aliases, member_aliases)
    for node in find_nodes_of_type(root, "lexical_declaration"):
        fragment = snapshot.content[node.start_byte : node.end_byte].decode("utf-8")
        alias, module_spec = _extract_require_assignment(fragment)
        if not alias or not module_spec:
            continue
        normalized = _normalize_import(module_spec, snapshot, module_name)
        if not normalized or not _is_internal_module(
            normalized, repo_prefix, module_index
        ):
            continue
        imports.append(normalized)
        import_aliases[alias] = normalized
    return imports, import_aliases, member_aliases


def _extract_module_spec(fragment: str) -> Optional[str]:
    fragment = fragment.strip()
    if "from" in fragment:
        parts = fragment.split("from", 1)[1].strip()
        return _string_literal(parts)
    if fragment.startswith("import"):
        remainder = fragment[len("import") :].strip()
        return _string_literal(remainder)
    if fragment.startswith("export"):
        return _string_literal(fragment)
    return None


def _string_literal(text: str) -> Optional[str]:
    for quote in ("'", '"'):
        if quote in text:
            start = text.find(quote)
            end = text.find(quote, start + 1)
            if start >= 0 and end > start:
                return text[start + 1 : end]
    return None


def _populate_ts_aliases(
    fragment: str,
    normalized: str,
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
) -> None:
    fragment = fragment.strip()
    if fragment.startswith("import") and "from" in fragment:
        head = fragment.split("from", 1)[0]
        if "{" in head and "}" in head:
            inner = head.split("{", 1)[1].rsplit("}", 1)[0]
            for part in inner.split(","):
                piece = part.strip()
                if not piece:
                    continue
                parts = piece.split(" as ", 1)
                name = parts[0].strip()
                alias = parts[1].strip() if len(parts) == 2 else None
                if name:
                    member_aliases[alias or name] = f"{normalized}.{name}"
        if "* as" in head:
            parts = head.split("* as", 1)[1].strip().split(",", 1)
            alias = parts[0].strip()
            if alias:
                import_aliases[alias] = normalized
        if "{" not in head and "*" not in head:
            parts = head.split()
            if len(parts) >= 2:
                alias = parts[1].strip().strip(",")
                if alias and alias not in {"from", "{"}:
                    import_aliases[alias] = normalized
    if fragment.startswith("import") and "require" in fragment and "=" in fragment:
        alias, _module = _extract_require_assignment(fragment)
        if alias:
            import_aliases[alias] = normalized
    if fragment.startswith("export") and "from" in fragment and "{" in fragment:
        inner = fragment.split("{", 1)[1].rsplit("}", 1)[0]
        for part in inner.split(","):
            piece = part.strip()
            if not piece:
                continue
            parts = piece.split(" as ", 1)
            name = parts[0].strip()
            alias = parts[1].strip() if len(parts) == 2 else None
            if name:
                member_aliases[alias or name] = f"{normalized}.{name}"


def _extract_require_assignment(fragment: str) -> tuple[str | None, str | None]:
    fragment = fragment.strip()
    if "require" not in fragment or "=" not in fragment:
        return None, None
    left, right = fragment.split("=", 1)
    alias = left.replace("const", "").replace("let", "").replace("var", "").strip()
    module = _string_literal(right)
    return (alias or None, module)


def _normalize_import(
    specifier: Optional[str], snapshot: FileSnapshot, module_name: str
) -> Optional[str]:
    if not specifier:
        return None
    spec = specifier.strip().strip("'\"")
    if not spec:
        return None
    if spec.startswith("."):
        parent = PurePosixPath(snapshot.record.relative_path.parent.as_posix())
        normalized = _normalize_relative_path(parent, PurePosixPath(spec))
        module_path = _normalize_ts_path(normalized.as_posix())
        repo_root = _repo_root_from_snapshot(snapshot)
        return module_name_from_path(
            repo_root,
            Path(module_path),
            strip_suffix=False,
            treat_init_as_package=False,
        )
    return spec.replace("/", ".")


def _normalize_relative_path(
    base: PurePosixPath, relative: PurePosixPath
) -> PurePosixPath:
    parts = list(base.parts)
    for part in relative.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return PurePosixPath(*parts)


def _normalize_ts_path(path: str) -> str:
    name = path
    if name.endswith(".d.ts"):
        name = name[: -len(".d.ts")]
    elif name.endswith(".tsx"):
        name = name[: -len(".tsx")]
    elif name.endswith(".ts"):
        name = name[: -len(".ts")]
    elif name.endswith(".mjs"):
        name = name[: -len(".mjs")]
    elif name.endswith(".cjs"):
        name = name[: -len(".cjs")]
    elif name.endswith(".js"):
        name = name[: -len(".js")]
    return name


def _repo_root_from_snapshot(snapshot: FileSnapshot) -> Path:
    rel_parts = snapshot.record.relative_path.parts
    if not rel_parts:
        return snapshot.record.path.parent
    return snapshot.record.path.parents[len(rel_parts) - 1]
