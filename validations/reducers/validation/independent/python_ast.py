# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import ast
from pathlib import Path
from typing import List

from .shared import AssignmentHint, CallEdge, Definition, FileParseResult, ImportEdge

_DYNAMIC_FUNCS = {"getattr", "globals", "locals", "__import__", "eval", "exec"}


class _CallVisitor(ast.NodeVisitor):
    def __init__(self, module_qname: str) -> None:
        self.module_qname = module_qname
        self.call_edges: List[CallEdge] = []
        self.defs: List[Definition] = []
        self.assignment_hints: List[AssignmentHint] = []
        self._scope_stack: List[tuple[str, str]] = []

    def _current_scope(self) -> str:
        if not self._scope_stack:
            return self.module_qname
        return self._scope_stack[-1][0]

    def _current_scope_kind(self) -> str:
        if not self._scope_stack:
            return "module"
        return self._scope_stack[-1][1]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        scope_kind = self._current_scope_kind()
        if scope_kind in {"function", "method"}:
            # Nested callables are treated as implementation detail; attribute calls
            # to the enclosing scope.
            self.generic_visit(node)
            return
        if scope_kind == "class":
            kind = "method"
            qname = f"{self._current_scope()}.{node.name}"
        else:
            kind = "function"
            qname = f"{self.module_qname}.{node.name}"
        self.defs.append(Definition(kind, qname, node.lineno, node.end_lineno or node.lineno))
        self._record_decorator_calls(qname, node.decorator_list)
        self._scope_stack.append((qname, kind))
        for statement in node.body:
            self.visit(statement)
        self._scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        scope_kind = self._current_scope_kind()
        if scope_kind in {"function", "method"}:
            self.generic_visit(node)
            return
        if scope_kind == "class":
            kind = "method"
            qname = f"{self._current_scope()}.{node.name}"
        else:
            kind = "function"
            qname = f"{self.module_qname}.{node.name}"
        self.defs.append(Definition(kind, qname, node.lineno, node.end_lineno or node.lineno))
        self._record_decorator_calls(qname, node.decorator_list)
        self._scope_stack.append((qname, kind))
        for statement in node.body:
            self.visit(statement)
        self._scope_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        scope_kind = self._current_scope_kind()
        if scope_kind in {"function", "method"}:
            # Nested classes inside callables are implementation detail.
            self.generic_visit(node)
            return
        if scope_kind == "class":
            qname = f"{self._current_scope()}.{node.name}"
        else:
            qname = f"{self.module_qname}.{node.name}"
        self.defs.append(Definition("class", qname, node.lineno, node.end_lineno or node.lineno))
        self._record_decorator_calls(qname, node.decorator_list)
        self._scope_stack.append((qname, "class"))
        for statement in node.body:
            self.visit(statement)
        self._scope_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        if self._current_scope_kind() not in {"function", "method"}:
            self.generic_visit(node)
            return
        callee, callee_qname, dynamic = _callee_name(node.func)
        callee_text = None
        try:
            callee_text = ast.unparse(node.func)
        except Exception:
            callee_text = None
        self.call_edges.append(
            CallEdge(
                caller=self._current_scope(),
                callee=callee or "",
                callee_qname=callee_qname,
                dynamic=dynamic or (not callee) or (callee in _DYNAMIC_FUNCS),
                callee_text=callee_text,
            )
        )
        self.generic_visit(node)

    def _assignment_value_text(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Call):
            callee, callee_qname, _ = _callee_name(node.func)
            return callee_qname or callee
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return _expr_name(node)
        return None

    def _record_decorator_calls(self, owner_qname: str, decorators: list[ast.AST]) -> None:
        for decorator in decorators:
            target = decorator.func if isinstance(decorator, ast.Call) else decorator
            callee, callee_qname, dynamic = _callee_name(target)
            callee_text = None
            try:
                callee_text = f"decorator:{ast.unparse(decorator)}"
            except Exception:
                callee_text = "decorator"
            self.call_edges.append(
                CallEdge(
                    caller=owner_qname,
                    callee=callee or "",
                    callee_qname=callee_qname,
                    dynamic=True if not callee else (dynamic or True),
                    callee_text=callee_text,
                )
            )

    def _record_assignment_target(self, target: ast.AST, value_text: str) -> None:
        receiver = None
        if isinstance(target, ast.Name):
            receiver = target.id
        elif isinstance(target, ast.Attribute):
            receiver = _expr_name(target)
        if receiver:
            self.assignment_hints.append(
                AssignmentHint(scope=self._current_scope(), receiver=receiver, value_text=value_text)
            )

    def visit_Assign(self, node: ast.Assign) -> None:
        value_text = self._assignment_value_text(node.value)
        if value_text and self._current_scope_kind() in {"function", "method"}:
            for target in node.targets:
                self._record_assignment_target(target, value_text)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        value_text = self._assignment_value_text(node.value) if node.value else None
        if value_text and self._current_scope_kind() in {"function", "method"}:
            self._record_assignment_target(node.target, value_text)
        self.generic_visit(node)


class _ImportVisitor(ast.NodeVisitor):
    def __init__(self, module_qname: str) -> None:
        self.module_qname = module_qname
        self.imports: List[ImportEdge] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name:
                target_text = alias.name
                if alias.asname:
                    target_text = f"{alias.name} as {alias.asname}"
                self.imports.append(
                    ImportEdge(
                        self.module_qname,
                        alias.name,
                        dynamic=False,
                        target_text=target_text,
                    )
                )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        prefix = "." * (node.level or 0)
        module = node.module or ""
        if module:
            for alias in node.names:
                symbol = alias.name
                if symbol == "*":
                    target_text = f"from {prefix}{module} import *"
                elif alias.asname:
                    target_text = f"from {prefix}{module} import {symbol} as {alias.asname}"
                else:
                    target_text = f"from {prefix}{module} import {symbol}"
                self.imports.append(
                    ImportEdge(
                        self.module_qname,
                        f"{prefix}{module}",
                        dynamic=False,
                        target_text=target_text,
                    )
                )
        else:
            for alias in node.names:
                if alias.name:
                    target_text = f"{prefix}{alias.name}"
                    if alias.asname:
                        target_text = f"{target_text} as {alias.asname}"
                    self.imports.append(
                        ImportEdge(
                            self.module_qname,
                            f"{prefix}{alias.name}",
                            dynamic=False,
                            target_text=target_text,
                        )
                    )



def _expr_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        root = _expr_name(node.value)
        if root:
            return f"{root}.{node.attr}"
        return node.attr
    return None


def _callee_name(node: ast.AST) -> tuple[str | None, str | None, bool]:
    if isinstance(node, ast.Name):
        return node.id, None, False
    if isinstance(node, ast.Attribute):
        dotted = _expr_name(node)
        return node.attr, dotted, False
    return None, None, True


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
            assignment_hints=[],
            parse_ok=False,
            error=str(exc),
        )

    call_visitor = _CallVisitor(module_qname)
    call_visitor.visit(tree)
    import_visitor = _ImportVisitor(module_qname)
    import_visitor.visit(tree)

    return FileParseResult(
        language="python",
        file_path=file_path,
        module_qualified_name=module_qname,
        defs=call_visitor.defs,
        call_edges=call_visitor.call_edges,
        import_edges=import_visitor.imports,
        assignment_hints=call_visitor.assignment_hints,
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
