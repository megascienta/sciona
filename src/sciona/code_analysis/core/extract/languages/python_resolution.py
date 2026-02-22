# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Python constructor and instance resolution utilities."""

from __future__ import annotations

from ...normalize.model import FileSnapshot


def node_text(node, content: bytes) -> str | None:
    if node is None:
        return None
    return content[node.start_byte : node.end_byte].decode("utf-8")


def resolve_constructor_target(
    callee_text: str,
    terminal: str,
    class_name_map: dict[str, str],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    raw_module_map: dict[str, str],
) -> str | None:
    if terminal in class_name_map:
        return class_name_map[terminal]
    if terminal in member_aliases:
        return member_aliases[terminal]
    if "." in callee_text:
        head, rest = callee_text.split(".", 1)
        if head in import_aliases:
            return f"{import_aliases[head]}.{rest}"
        for raw, normalized in raw_module_map.items():
            if callee_text == raw or callee_text.startswith(f"{raw}."):
                suffix = callee_text[len(raw) :].lstrip(".")
                return f"{normalized}.{suffix}" if suffix else normalized
    return None


def collect_module_instance_map(
    root,
    snapshot: FileSnapshot,
    class_name_map: dict[str, str],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    raw_module_map: dict[str, str],
) -> dict[str, str]:
    instance_map: dict[str, str] = {}

    def walk(node) -> None:
        if node is None:
            return
        if node.type in {"function_definition", "class_definition"}:
            return
        if node.type == "assignment":
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            if (
                left is not None
                and right is not None
                and right.type == "call"
                and left.type == "identifier"
            ):
                name = node_text(left, snapshot.content)
                callee = right.child_by_field_name("function")
                callee_text = node_text(callee, snapshot.content) or ""
                terminal = callee_text.split(".")[-1] if callee_text else ""
                target = resolve_constructor_target(
                    callee_text,
                    terminal,
                    class_name_map,
                    import_aliases,
                    member_aliases,
                    raw_module_map,
                )
                if name and target:
                    instance_map[name] = target
        for child in getattr(node, "children", []):
            walk(child)

    walk(root)
    return instance_map


def collect_callable_instance_map(
    body_node,
    snapshot: FileSnapshot,
    class_name_map: dict[str, str],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    raw_module_map: dict[str, str],
) -> dict[str, str]:
    if body_node is None:
        return {}
    instance_map: dict[str, str] = {}

    def walk(node) -> None:
        if node is None:
            return
        if node.type in {"function_definition", "class_definition", "lambda"}:
            return
        if node.type == "assignment":
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            if (
                left is not None
                and right is not None
                and right.type == "call"
            ):
                name = None
                if left.type == "identifier":
                    name = node_text(left, snapshot.content)
                elif left.type == "attribute":
                    object_node = left.child_by_field_name("object")
                    attribute_node = left.child_by_field_name("attribute")
                    object_name = node_text(object_node, snapshot.content) or ""
                    if object_name in {"self", "cls"}:
                        name = node_text(attribute_node, snapshot.content)
                    if not name:
                        left_text = node_text(left, snapshot.content) or ""
                        if left_text.startswith("self.") or left_text.startswith("cls."):
                            parts = left_text.split(".", 2)
                            if len(parts) >= 2:
                                name = parts[1]
                callee = right.child_by_field_name("function")
                callee_text = node_text(callee, snapshot.content) or ""
                terminal = callee_text.split(".")[-1] if callee_text else ""
                target = resolve_constructor_target(
                    callee_text,
                    terminal,
                    class_name_map,
                    import_aliases,
                    member_aliases,
                    raw_module_map,
                )
                if name and target:
                    instance_map[name] = target
        for child in getattr(node, "children", []):
            walk(child)

    walk(body_node)
    return instance_map


def collect_class_instance_map(
    class_body_node,
    snapshot: FileSnapshot,
    class_name_map: dict[str, str],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    raw_module_map: dict[str, str],
) -> dict[str, str]:
    if class_body_node is None:
        return {}
    instance_map: dict[str, str] = {}

    def walk(node) -> None:
        if node is None:
            return
        if node.type in {"class_definition", "lambda"}:
            return
        if node.type == "assignment":
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            if left is not None and right is not None and right.type == "call":
                name = None
                if left.type == "attribute":
                    object_node = left.child_by_field_name("object")
                    attribute_node = left.child_by_field_name("attribute")
                    object_name = node_text(object_node, snapshot.content) or ""
                    if object_name in {"self", "cls"}:
                        name = node_text(attribute_node, snapshot.content)
                    if not name:
                        left_text = node_text(left, snapshot.content) or ""
                        if left_text.startswith("self.") or left_text.startswith("cls."):
                            parts = left_text.split(".", 2)
                            if len(parts) >= 2:
                                name = parts[1]
                if name:
                    callee = right.child_by_field_name("function")
                    callee_text = node_text(callee, snapshot.content) or ""
                    terminal = callee_text.split(".")[-1] if callee_text else ""
                    target = resolve_constructor_target(
                        callee_text,
                        terminal,
                        class_name_map,
                        import_aliases,
                        member_aliases,
                        raw_module_map,
                    )
                    if target:
                        instance_map[name] = target
        for child in getattr(node, "children", []):
            walk(child)

    walk(class_body_node)
    return instance_map
