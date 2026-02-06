"""Language-specific symbol introspection helpers for profile reducers."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from tree_sitter import Parser
from tree_sitter_languages import get_language


def python_function_extras(
    language: str,
    repo_root: Optional[Path],
    file_path: str,
    start_line: int,
    end_line: int,
) -> Tuple[List[str], bool, Optional[Tuple[int, int]], List[str]]:
    """Return parameters + docstring location info for Python functions."""
    if language != "python" or repo_root is None:
        return [], False, None, []
    inspector = _python_inspector(repo_root, file_path)
    if not inspector:
        return [], False, None, []
    details = inspector.function_details(start_line, end_line)
    if not details:
        return [], False, None, []
    return (
        details.parameters,
        details.has_docstring,
        details.docstring_span,
        details.decorators,
    )


def python_class_extras(
    language: str,
    repo_root: Optional[Path],
    file_path: str,
    start_line: int,
    end_line: int,
) -> Tuple[List[str], List[str], bool, Optional[Tuple[int, int]]]:
    """Return decorator/base metadata for Python classes."""
    if language != "python" or repo_root is None:
        return [], [], False, None
    inspector = _python_inspector(repo_root, file_path)
    if not inspector:
        return [], [], False, None
    details = inspector.class_details(start_line, end_line)
    if not details:
        return [], [], False, None
    return (
        details.decorators,
        details.bases,
        details.has_docstring,
        details.docstring_span,
    )


def typescript_function_extras(
    language: str,
    repo_root: Optional[Path],
    file_path: str,
    start_line: int,
    end_line: int,
) -> Tuple[List[str], List[str]]:
    """Return parameter names and decorators for TypeScript functions."""
    if language != "typescript" or repo_root is None:
        return [], []
    inspector = _typescript_inspector(repo_root, file_path)
    parameters: List[str] = []
    decorators: List[str] = []
    if inspector:
        details = inspector.function_details(start_line, end_line)
        if details:
            parameters = details.parameters
            decorators = details.decorators
    if not parameters:
        fallback = _line_based_ts_parameters(
            repo_root / file_path, start_line, end_line
        )
        if fallback:
            parameters = fallback
    return parameters, decorators


def typescript_class_extras(
    language: str,
    repo_root: Optional[Path],
    file_path: str,
    start_line: int,
    end_line: int,
) -> Tuple[List[str], List[str]]:
    """Return decorators + base clauses for TypeScript classes."""
    if language != "typescript" or repo_root is None:
        return [], []
    inspector = _typescript_inspector(repo_root, file_path)
    if not inspector:
        return [], []
    details = inspector.class_details(start_line, end_line)
    if not details:
        return [], []
    return details.decorators, details.bases


@dataclass
class _FunctionDetails:
    parameters: List[str]
    has_docstring: bool
    docstring_span: Optional[Tuple[int, int]]
    decorators: List[str]


@dataclass
class _ClassDetails:
    decorators: List[str]
    bases: List[str]
    has_docstring: bool
    docstring_span: Optional[Tuple[int, int]]


class _PythonInspector:
    def __init__(self, source: str) -> None:
        self._tree = ast.parse(source)
        self.functions: Dict[Tuple[int, int], _FunctionDetails] = {}
        self.classes: Dict[Tuple[int, int], _ClassDetails] = {}
        self._scan(self._tree, 0)

    def function_details(
        self, start_line: int, end_line: int
    ) -> Optional[_FunctionDetails]:
        return self.functions.get((start_line, end_line))

    def class_details(self, start_line: int, end_line: int) -> Optional[_ClassDetails]:
        return self.classes.get((start_line, end_line))

    def _scan(self, node: ast.AST, depth: int) -> None:
        if depth > _MAX_AST_DEPTH:
            return
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._record_function(child)
            if isinstance(child, ast.ClassDef):
                self._record_class(child)
            self._scan(child, depth + 1)

    def _record_function(self, node: ast.AST) -> None:
        lineno = getattr(node, "lineno", None)
        end_lineno = getattr(node, "end_lineno", None)
        if lineno is None or end_lineno is None:
            return
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return
        doc_span = _docstring_span(node)
        self.functions[(lineno, end_lineno)] = _FunctionDetails(
            parameters=_collect_parameters(node.args),
            has_docstring=doc_span is not None,
            docstring_span=doc_span,
            decorators=[
                _safe_unparse(entry) for entry in getattr(node, "decorator_list", [])
            ],
        )

    def _record_class(self, node: ast.ClassDef) -> None:
        lineno = getattr(node, "lineno", None)
        end_lineno = getattr(node, "end_lineno", None)
        if lineno is None or end_lineno is None:
            return
        bases = [_safe_unparse(entry) for entry in node.bases]
        for keyword in node.keywords:
            expr = _safe_unparse(keyword.value)
            if keyword.arg:
                bases.append(f"{keyword.arg}={expr}")
            else:
                bases.append(expr)
        doc_span = _docstring_span(node)
        self.classes[(lineno, end_lineno)] = _ClassDetails(
            decorators=[_safe_unparse(entry) for entry in node.decorator_list],
            bases=bases,
            has_docstring=doc_span is not None,
            docstring_span=doc_span,
        )


def _python_inspector(
    repo_root: Path, relative_path: str
) -> Optional[_PythonInspector]:
    return _python_inspector_cached(str(repo_root.resolve()), relative_path)


@lru_cache(maxsize=128)
def _python_inspector_cached(
    root_key: str, relative_path: str
) -> Optional[_PythonInspector]:
    path = Path(root_key) / relative_path
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        return _PythonInspector(source)
    except SyntaxError:
        return None


def _collect_parameters(args: ast.arguments) -> List[str]:
    params: List[str] = []
    for entry in getattr(args, "posonlyargs", []):
        params.append(entry.arg)
    for entry in args.args:
        params.append(entry.arg)
    if args.vararg:
        params.append(f"*{args.vararg.arg}")
    if getattr(args, "kwonlyargs", None):
        for entry in args.kwonlyargs:
            params.append(entry.arg)
    if args.kwarg:
        params.append(f"**{args.kwarg.arg}")
    return params


def _safe_unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node).strip()
    except AttributeError:
        return ast.dump(node)
    except ValueError:
        return ""


def _docstring_span(node: ast.AST) -> Optional[Tuple[int, int]]:
    body = getattr(node, "body", None)
    if not body or not isinstance(body, list) or not body:
        return None
    expr = body[0]
    if isinstance(expr, ast.Expr):
        value = getattr(expr, "value", None)
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            lineno = getattr(expr, "lineno", None)
            end_lineno = getattr(expr, "end_lineno", None)
            if lineno is not None and end_lineno is not None:
                return lineno, end_lineno
    return None


_MAX_AST_DEPTH = 2000


@dataclass
class _TypeScriptFunctionDetails:
    parameters: List[str]
    decorators: List[str]


@dataclass
class _TypeScriptClassDetails:
    decorators: List[str]
    bases: List[str]


class _TypeScriptInspector:
    _PARSER: Parser | None = None

    def __init__(self, source: str) -> None:
        if _TypeScriptInspector._PARSER is None:
            parser = Parser()
            language = get_language("typescript")
            if hasattr(parser, "set_language"):
                parser.set_language(language)
            else:
                parser.language = language
            _TypeScriptInspector._PARSER = parser
        assert _TypeScriptInspector._PARSER is not None
        tree = _TypeScriptInspector._PARSER.parse(source.encode("utf-8"))
        self._source = source
        self.functions: Dict[Tuple[int, int], _TypeScriptFunctionDetails] = {}
        self.classes: Dict[Tuple[int, int], _TypeScriptClassDetails] = {}
        self._scan(tree.root_node)

    def function_details(
        self, start_line: int, end_line: int
    ) -> Optional[_TypeScriptFunctionDetails]:
        return self.functions.get((start_line, end_line))

    def class_details(
        self, start_line: int, end_line: int
    ) -> Optional[_TypeScriptClassDetails]:
        return self.classes.get((start_line, end_line))

    def _scan(self, node) -> None:
        node_type = getattr(node, "type", "")
        if node_type in {"function_declaration", "method_definition"}:
            self._record_function(node)
        if node_type == "class_declaration":
            self._record_class(node)
        for child in getattr(node, "children", []):
            self._scan(child)

    def _record_function(self, node) -> None:
        lineno = node.start_point[0] + 1
        end_lineno = node.end_point[0] + 1
        params_node = node.child_by_field_name("parameters")
        parameters: List[str] = []
        if params_node:
            text = self._slice(params_node.start_byte, params_node.end_byte)
            parameters = _parse_typescript_parameters(text)
        else:
            fragment = _find_parameter_fragment(
                self._source, node.start_byte, node.end_byte
            )
            if fragment:
                parameters = _parse_typescript_parameters(fragment)
        decorators = _collect_ts_decorators(node, self._source)
        self.functions[(lineno, end_lineno)] = _TypeScriptFunctionDetails(
            parameters=parameters, decorators=decorators
        )

    def _record_class(self, node) -> None:
        lineno = node.start_point[0] + 1
        end_lineno = node.end_point[0] + 1
        decorators = _collect_ts_decorators(node, self._source)
        bases: List[str] = []
        heritage = node.child_by_field_name("heritage")
        if heritage:
            text = self._slice(heritage.start_byte, heritage.end_byte)
            bases = _parse_typescript_bases(text)
        self.classes[(lineno, end_lineno)] = _TypeScriptClassDetails(
            decorators=decorators, bases=bases
        )

    def _slice(self, start: int, end: int) -> str:
        return self._source.encode("utf-8")[start:end].decode("utf-8")


def _typescript_inspector(
    repo_root: Path, relative_path: str
) -> Optional[_TypeScriptInspector]:
    return _typescript_inspector_cached(str(repo_root.resolve()), relative_path)


@lru_cache(maxsize=128)
def _typescript_inspector_cached(
    root_key: str, relative_path: str
) -> Optional[_TypeScriptInspector]:
    path = Path(root_key) / relative_path
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        return _TypeScriptInspector(source)
    except SyntaxError:
        return None


def _parse_typescript_parameters(fragment: str) -> List[str]:
    stripped = fragment.strip()
    if not stripped.startswith("(") or not stripped.endswith(")"):
        return []
    inner = stripped[1:-1].strip()
    if not inner:
        return []
    params: List[str] = []
    for raw in inner.split(","):
        piece = raw.strip()
        if not piece:
            continue
        piece = piece.split("=")[0].strip()
        piece = piece.split(":")[0].strip()
        params.append(piece)
    return params


def _parse_typescript_bases(heritage: str) -> List[str]:
    bases: List[str] = []
    fragments = heritage.replace("implements", ",").replace("extends", ",").split(",")
    for fragment in fragments:
        entry = fragment.strip().strip("{").strip("}")
        if entry:
            bases.append(entry)
    return bases


def _collect_ts_decorators(node, source: str) -> List[str]:
    decorators: List[str] = []
    if not hasattr(node, "children"):
        return decorators
    for child in node.children:
        if child.type == "decorator":
            text = (
                source.encode("utf-8")[child.start_byte : child.end_byte]
                .decode("utf-8")
                .strip()
            )
            decorators.append(text)
    return decorators


def _find_parameter_fragment(
    source: str, start_byte: int, end_byte: int
) -> Optional[str]:
    segment = source.encode("utf-8")[start_byte:end_byte].decode("utf-8")
    start = segment.find("(")
    end = segment.find(")", start + 1)
    if start == -1 or end == -1:
        return None
    return segment[start : end + 1]


def _line_based_ts_parameters(path: Path, start_line: int, end_line: int) -> List[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    snippet = "\n".join(lines[start_line - 1 : end_line])
    start = snippet.find("(")
    end = snippet.find(")", start + 1)
    if start == -1 or end == -1:
        return []
    fragment = snippet[start : end + 1]
    return _parse_typescript_parameters(fragment)


__all__ = [
    "python_class_extras",
    "python_function_extras",
    "typescript_class_extras",
    "typescript_function_extras",
]
