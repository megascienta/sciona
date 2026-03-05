# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Python constructor and instance resolution utilities."""

from __future__ import annotations

from .python_resolution_aliases import (
    _callable_chain,
    _raw_module_chain_map,
    _resolve_alias_target,
    attribute_chain,
    node_text,
    resolve_constructor_target,
    unique_class_match,
)
from .python_resolution_instances import (
    collect_callable_local_bindings,
    collect_callable_instance_map,
    collect_class_instance_map,
    collect_module_instance_map,
)
from .python_resolution_types import (
    _type_annotation_chain,
    _typed_parameters_for_body_node,
    _typed_parameters_for_callable_node,
    _typed_parameters_for_enclosing_callable,
)


__all__ = [
    "_callable_chain",
    "_raw_module_chain_map",
    "_resolve_alias_target",
    "_type_annotation_chain",
    "_typed_parameters_for_body_node",
    "_typed_parameters_for_callable_node",
    "_typed_parameters_for_enclosing_callable",
    "collect_callable_local_bindings",
    "attribute_chain",
    "collect_callable_instance_map",
    "collect_class_instance_map",
    "collect_module_instance_map",
    "node_text",
    "resolve_constructor_target",
    "unique_class_match",
]
