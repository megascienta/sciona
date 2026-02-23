# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Java call extraction and resolution utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ....tools.call_extraction import CallTarget
from .call_resolution_kernel import (
    CallResolutionAdapter,
    CallResolutionRequest,
    resolve_with_adapter,
    resolve_with_mode,
)


def callee_text(call_node, callee_node, content: bytes) -> str | None:
    if call_node is None:
        return node_text(callee_node, content)
    if call_node.type == "method_invocation":
        name_node = call_node.child_by_field_name("name")
        object_node = call_node.child_by_field_name("object")
        name = node_text(name_node or callee_node, content)
        if object_node is not None:
            obj = node_text(object_node, content)
            if obj and name:
                return f"{obj}.{name}"
        return name
    if call_node.type == "object_creation_expression":
        type_node = call_node.child_by_field_name("type")
        return node_text(type_node, content) or node_text(callee_node, content)
    return node_text(callee_node, content)


def resolve_java_calls(
    targets: List[CallTarget],
    module_name: str,
    module_functions: set[str],
    class_methods: dict[str, set[str]],
    class_name_map: dict[str, str],
    class_name_candidates: dict[str, set[str]],
    import_class_map: dict[str, str],
    class_name: str | None,
    instance_types: dict[str, str],
    module_prefix: str | None,
    qualify_java_type,
) -> List[str]:
    class_method_names = class_methods.get(class_name, set()) if class_name else set()
    requests = _to_requests(targets)
    adapter = _JavaCallAdapter(
        module_name=module_name,
        module_functions=module_functions,
        class_name=class_name,
        class_method_names=class_method_names,
        class_methods=class_methods,
        class_name_map=class_name_map,
        class_name_candidates=class_name_candidates,
        import_class_map=import_class_map,
        instance_types=instance_types,
        module_prefix=module_prefix,
        qualify_java_type=qualify_java_type,
    )
    return resolve_with_mode(
        shared_resolver=lambda: resolve_with_adapter(requests, adapter),
    )


@dataclass(frozen=True)
class _JavaCallAdapter(CallResolutionAdapter):
    module_name: str
    module_functions: set[str]
    class_name: str | None
    class_method_names: set[str]
    class_methods: dict[str, set[str]]
    class_name_map: dict[str, str]
    class_name_candidates: dict[str, set[str]]
    import_class_map: dict[str, str]
    instance_types: dict[str, str]
    module_prefix: str | None
    qualify_java_type: object

    def resolve(self, request: CallResolutionRequest) -> List[str]:
        terminal = request.terminal
        raw = request.callee_text
        receiver_hint = request.receiver
        if "." in raw:
            receiver = raw.rsplit(".", 1)[0].strip()
            receiver_simple = receiver.rsplit(".", 1)[-1]
            if receiver_hint and receiver_simple != receiver_hint:
                receiver_simple = receiver_hint
            instance_type = self.instance_types.get(receiver_simple)
            if instance_type:
                qualified_type = self.qualify_java_type(
                    instance_type,
                    self.module_name,
                    self.class_name_candidates,
                    self.import_class_map,
                    self.module_prefix,
                )
                if qualified_type:
                    return [f"{qualified_type}.{terminal}"]
            if receiver_simple[:1].isupper():
                import_target = self.import_class_map.get(receiver_simple)
                local_class = _unique_class_candidate(
                    receiver_simple,
                    self.class_name_candidates,
                )
                if import_target:
                    return [f"{import_target}.{terminal}"]
                if local_class:
                    return [f"{local_class}.{terminal}"]
        if is_unqualified(raw):
            import_target = self.import_class_map.get(terminal)
            local_class = _unique_class_candidate(
                terminal,
                self.class_name_candidates,
            )
            if import_target:
                return [f"{import_target}.{terminal}"]
            if local_class:
                return [f"{local_class}.{terminal}"]
        if self.class_name and terminal in self.class_method_names:
            if is_receiver_call(raw) or is_unqualified(raw):
                return [f"{self.class_name}.{terminal}"]
        if is_unqualified(raw) and terminal in self.module_functions:
            return [f"{self.module_name}.{terminal}"]
        class_qualified = _unique_class_candidate(
            terminal,
            self.class_name_candidates,
        )
        if class_qualified and terminal in self.class_methods.get(class_qualified, set()):
            return [f"{class_qualified}.{terminal}"]
        return []


def _to_requests(targets: List[CallTarget]) -> list[CallResolutionRequest]:
    return [
        CallResolutionRequest(
            terminal=target.terminal,
            callee_text=(target.callee_text or "").strip(),
            receiver=target.receiver,
            receiver_chain=target.receiver_chain,
            callee_kind=target.callee_kind,
        )
        for target in targets
    ]


def is_unqualified(callee_text_raw: str) -> bool:
    return "." not in callee_text_raw


def is_receiver_call(callee_text_raw: str) -> bool:
    return callee_text_raw.startswith("this.") or callee_text_raw.startswith("super.")


def node_text(node, content: bytes) -> str | None:
    if node is None:
        return None
    return content[node.start_byte : node.end_byte].decode("utf-8")


def _unique_class_candidate(
    simple_name: str,
    class_name_candidates: dict[str, set[str]],
) -> str | None:
    candidates = class_name_candidates.get(simple_name) or set()
    if len(candidates) == 1:
        return next(iter(candidates))
    return None
