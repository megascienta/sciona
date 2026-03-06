# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Typed payloads exposed to reducers and addon consumers."""

from __future__ import annotations

from typing import Dict, List, Sequence, TypedDict


class ModuleOverviewPayload(TypedDict, total=False):
    projection: str
    projection_version: str
    payload_kind: str
    module_structural_id: str
    module_qualified_name: str
    language: str
    file_path: str
    line_span: Sequence[int]
    start_byte: int
    end_byte: int
    content_hash: str
    files: List[str]
    file_count: int
    module_files: List[Dict[str, str]] | None
    module_file_count: int
    classifiers: List[Dict[str, str]]
    functions: List[Dict[str, str]]
    methods: List[Dict[str, str]]
    nested_classifiers: List[Dict[str, str]]
    node_counts: Dict[str, int]
    language_breakdown: Dict[str, int]
    imports: List[Dict[str, str]]
    artifact_available: bool
    edge_source: str


class ClassifierOverviewPayload(TypedDict, total=False):
    projection: str
    projection_version: str
    payload_kind: str
    classifier_id: str
    module_qualified_name: str
    language: str
    file_path: str
    line_span: Sequence[int]
    start_byte: int
    end_byte: int
    content_hash: str
    methods: List[Dict[str, str]]
    bases: List[str]
    artifact_available: bool
    edge_source: str


class CallableOverviewPayload(TypedDict, total=False):
    projection: str
    projection_version: str
    payload_kind: str
    callable_id: str
    requested_identifier: str
    module_qualified_name: str
    language: str
    file_path: str
    line_span: Sequence[int]
    start_byte: int
    end_byte: int
    content_hash: str
    callable_role: str | None
    callable_role_source: str
    parameters: List[str]
    signature: str
    parent_structural_id: str | None
    parent_type: str | None
    parent_qualified_name: str | None
    artifact_available: bool
    edge_source: str


class StructuralIndexPayload(TypedDict, total=False):
    projection: str
    projection_version: str
    payload_kind: str
    modules: Dict[str, object]
    files: Dict[str, object]
    classifiers: Dict[str, object]
    functions: Dict[str, object]
    methods: Dict[str, object]
    imports: Dict[str, object]
    import_cycles: List[Dict[str, object]]
