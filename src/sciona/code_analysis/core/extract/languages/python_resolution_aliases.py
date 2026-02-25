# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Alias and constructor target resolution for Python extraction."""

from __future__ import annotations

from .symbol_ir import resolve_alias


def node_text(node, content: bytes) -> str | None:
    if node is None:
        return None
    text = getattr(node, "text", None)
    if text:
        return text.decode("utf-8")
    return content[node.start_byte : node.end_byte].decode("utf-8")


def attribute_chain(node, content: bytes) -> tuple[str, ...]:
    if node is None:
        return ()
    if node.type == "identifier":
        value = node_text(node, content)
        return (value,) if value else ()
    if node.type != "attribute":
        return ()
    object_node = node.child_by_field_name("object")
    attribute_node = node.child_by_field_name("attribute")
    head = attribute_chain(object_node, content)
    tail = node_text(attribute_node, content) if attribute_node is not None else None
    if not tail:
        return ()
    return (*head, tail)


def _callable_chain(node, content: bytes) -> tuple[str, ...]:
    if node is None:
        return ()
    if node.type == "identifier":
        value = node_text(node, content)
        return (value,) if value else ()
    return attribute_chain(node, content)


def unique_class_match(
    simple_name: str,
    class_name_candidates: dict[str, set[str]],
) -> str | None:
    candidates = class_name_candidates.get(simple_name) or set()
    if len(candidates) == 1:
        return next(iter(candidates))
    return None


def _raw_module_chain_map(raw_module_map: dict[str, str]) -> dict[tuple[str, ...], str]:
    chain_map: dict[tuple[str, ...], str] = {}
    for raw, normalized in raw_module_map.items():
        chain = tuple(part for part in raw.split(".") if part)
        if chain:
            chain_map[chain] = normalized
    return chain_map


def resolve_constructor_target(
    callee_chain: tuple[str, ...],
    terminal_hint: str | None,
    class_name_candidates: dict[str, set[str]],
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
    raw_module_map: dict[str, str],
) -> str | None:
    terminal = terminal_hint or (callee_chain[-1] if callee_chain else "")
    class_match = unique_class_match(terminal, class_name_candidates)
    if class_match:
        return class_match
    if terminal in member_aliases:
        return member_aliases[terminal]
    if len(callee_chain) > 1:
        head = callee_chain[0]
        if head in import_aliases:
            return f"{import_aliases[head]}.{'.'.join(callee_chain[1:])}"
        for raw_chain, normalized in _raw_module_chain_map(raw_module_map).items():
            if (
                len(callee_chain) < len(raw_chain)
                or callee_chain[: len(raw_chain)] != raw_chain
            ):
                continue
            suffix = callee_chain[len(raw_chain) :]
            return f"{normalized}.{'.'.join(suffix)}" if suffix else normalized
    return None


def _resolve_alias_target(
    node,
    content: bytes,
    known_instances: dict[str, str],
) -> str | None:
    if node is None:
        return None
    if node.type == "identifier":
        name = node_text(node, content)
        return resolve_alias(name or "", instance_map=known_instances)
    if node.type == "attribute":
        chain = attribute_chain(node, content)
        if not chain:
            return None
        if len(chain) >= 2 and chain[0] in {"self", "cls"}:
            return resolve_alias(chain[1], instance_map=known_instances)
        return resolve_alias(".".join(chain), instance_map=known_instances)
    return None


__all__ = [
    "_callable_chain",
    "_raw_module_chain_map",
    "_resolve_alias_target",
    "attribute_chain",
    "node_text",
    "resolve_constructor_target",
    "unique_class_match",
]
