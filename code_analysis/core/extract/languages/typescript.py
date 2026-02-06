"""TypeScript Tree-sitter analyzer."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import List, Optional

from ....tools.tree_sitter import build_parser

from ...module_naming import module_name_from_path
from ....tools.call_extraction import collect_call_identifiers
from ...normalize.model import (
    AnalysisResult,
    CallRecord,
    EdgeRecord,
    FileSnapshot,
    SemanticNodeRecord,
)
from ..analyzer import ASTAnalyzer
from ..utils import count_lines, find_nodes_of_type


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
            root = tree.root_node
            for child in root.children:
                self._walk(child, snapshot, module_name, result, class_stack)

            # Extract imports (v1: import_statement only; best-effort, syntax-only).
            imports: List[str] = []
            for import_node in find_nodes_of_type(root, "import_statement"):
                target = snapshot.content[
                    import_node.start_byte : import_node.end_byte
                ].decode("utf-8")
                module = _extract_ts_import(target)
                normalized = _normalize_ts_import(module, snapshot, module_name)
                if normalized:
                    imports.append(normalized)

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
            if body:
                for child in body.children:
                    self._walk(child, snapshot, module_name, result, class_stack)
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
            else:
                node_type = "function"
                parent = module_name
                parent_node_type = "module"
                qualified = f"{module_name}.{func_name}"
                edge_type = "CONTAINS"
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
            calls = collect_call_identifiers(
                body_node,
                snapshot.content,
                call_node_types={"call_expression"},
                skip_node_types={
                    "class_declaration",
                    "function_declaration",
                    "method_definition",
                    "function_expression",
                    "arrow_function",
                },
            )
            if calls:
                result.call_records.append(
                    CallRecord(
                        qualified_name=qualified,
                        node_type=node_type,
                        callee_identifiers=list(calls),
                    )
                )
            return

        for child in getattr(node, "children", []):
            self._walk(child, snapshot, module_name, result, class_stack)


def module_name(repo_root: Path, snapshot: FileSnapshot) -> str:
    return module_name_from_path(
        repo_root,
        snapshot.record.relative_path,
        strip_suffix=True,
        treat_init_as_package=False,
    )


def _extract_ts_import(fragment: str) -> Optional[str]:
    fragment = fragment.strip()
    if "from" in fragment:
        parts = fragment.split("from", 1)[1].strip()
        if parts.startswith("'") or parts.startswith('"'):
            return parts.strip("'\"").rstrip(";")
    elif fragment.startswith("import"):
        remainder = fragment[len("import") :].strip()
        if remainder.startswith("'") or remainder.startswith('"'):
            return remainder.strip("'\"").rstrip(";")
    return None


def _normalize_ts_import(
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
