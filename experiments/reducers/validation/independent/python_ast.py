# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import ast
from pathlib import Path
from typing import List

from .shared import CallEdge, Definition, FileParseResult, ImportEdge

_DYNAMIC_FUNCS = {"getattr", "globals", "locals", "__import__", "eval", "exec"}


class _CallVisitor(ast.NodeVisitor):
    def __init__(self, module_qname: str) -> None:
        self.module_qname = module_qname
        self.call_edges: List[CallEdge] = []
        self.defs: List[Definition] = []
        self._scope_stack: List[str] = []

    def _current_scope(self) -> str:
        if not self._scope_stack:
            return self.module_qname
        return self._scope_stack[-1]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        qname = f"{self.module_qname}.{node.name}"
        self.defs.append(Definition("function", qname, node.lineno, node.end_lineno or node.lineno))
        self._scope_stack.append(qname)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        qname = f"{self.module_qname}.{node.name}"
        self.defs.append(Definition("function", qname, node.lineno, node.end_lineno or node.lineno))
        self._scope_stack.append(qname)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qname = f"{self.module_qname}.{node.name}"
        self.defs.append(Definition("class", qname, node.lineno, node.end_lineno or node.lineno))
        self._scope_stack.append(qname)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        callee, dynamic = _callee_name(node.func)
        if callee:
            callee_qname = None
            if callee.isidentifier():
                callee_qname = f"{self.module_qname}.{callee}"
            self.call_edges.append(
                CallEdge(
                    caller=self._current_scope(),
                    callee=callee,
                    callee_qname=callee_qname,
                    dynamic=dynamic or (callee in _DYNAMIC_FUNCS),
                )
            )
        self.generic_visit(node)


class _ImportVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imports: List[ImportEdge] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name:
                self.imports.append(ImportEdge("", alias.name, dynamic=False))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        prefix = "." * (node.level or 0)
        module = node.module or ""
        if module:
            self.imports.append(ImportEdge("", f"{prefix}{module}", dynamic=False))
        else:
            for alias in node.names:
                if alias.name:
                    self.imports.append(ImportEdge("", f"{prefix}{alias.name}", dynamic=False))



def _callee_name(node: ast.AST) -> tuple[str | None, bool]:
    if isinstance(node, ast.Name):
        return node.id, False
    if isinstance(node, ast.Attribute):
        return node.attr, False
    if isinstance(node, ast.Call):
        return None, True
    return None, False


def parse_python_file(repo_root: Path, file_path: str, module_qname: str) -> FileParseResult:
    full_path = repo_root / file_path
    try:
        source = full_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception as exc:
        return FileParseResult(
            language="python",
            file_path=file_path,
            module_qualified_name=module_qname,
            defs=[],
            call_edges=[],
            import_edges=[],
            parse_ok=False,
            error=str(exc),
        )

    call_visitor = _CallVisitor(module_qname)
    call_visitor.visit(tree)
    import_visitor = _ImportVisitor()
    import_visitor.visit(tree)

    return FileParseResult(
        language="python",
        file_path=file_path,
        module_qualified_name=module_qname,
        defs=call_visitor.defs,
        call_edges=call_visitor.call_edges,
        import_edges=import_visitor.imports,
        parse_ok=True,
    )


def parse_python_files(repo_root: Path, files: List[dict]) -> List[FileParseResult]:
    results: List[FileParseResult] = []
    for entry in files:
        results.append(
            parse_python_file(
                repo_root,
                entry["file_path"],
                entry["module_qualified_name"],
            )
        )
    return results
