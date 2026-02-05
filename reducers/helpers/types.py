"""Typed payloads exposed to prompt reducers."""
from __future__ import annotations

from typing import Dict, List, Sequence, TypedDict


class ModuleOverviewPayload(TypedDict, total=False):
    projection: str
    projection_version: str
    module_structural_id: str
    module_qualified_name: str
    language: str
    file_path: str
    line_span: Sequence[int]
    content_hash: str
    files: List[str]
    file_count: int
    classes: List[Dict[str, str]]
    functions: List[Dict[str, str]]
    methods: List[Dict[str, str]]
    node_counts: Dict[str, int]
    language_breakdown: Dict[str, int]
    imports: List[Dict[str, str]]


class ClassOverviewPayload(TypedDict, total=False):
    projection: str
    projection_version: str
    class_structural_id: str
    class_id: str
    module_qualified_name: str
    language: str
    file_path: str
    line_span: Sequence[int]
    content_hash: str
    methods: List[Dict[str, str]]


class FunctionOverviewPayload(TypedDict, total=False):
    projection: str
    projection_version: str
    function_structural_id: str
    function_id: str
    module_qualified_name: str
    language: str
    file_path: str
    line_span: Sequence[int]
    content_hash: str
    parameters: List[str]
    decorators: List[str]
    docstring: bool


class StructuralIndexPayload(TypedDict, total=False):
    projection: str
    projection_version: str
    modules: Dict[str, object]
    files: Dict[str, object]
    classes: Dict[str, object]
    functions: Dict[str, object]
    methods: Dict[str, object]
    imports: Dict[str, object]
    import_cycles: List[Dict[str, object]]
