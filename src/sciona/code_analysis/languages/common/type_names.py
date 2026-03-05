# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Helpers for normalizing typed references used in constructor resolution."""

from __future__ import annotations


def type_base_name(type_text: str) -> str:
    text = type_text.strip().lstrip(":").strip()
    if not text:
        return ""
    text = _strip_prefix(text, "readonly ")
    text = _strip_prefix(text, "new ")
    text = _strip_suffix(text, "?")
    text = _strip_suffix(text, "!")
    text = _strip_arrays(text)
    if "|" in text:
        text = text.split("|", 1)[0].strip()
    if "&" in text:
        text = text.split("&", 1)[0].strip()
    for open_char, close_char in (("<", ">"), ("[", "]")):
        inner = _outer_type_argument(text, open_char, close_char)
        if inner is not None:
            first_arg = _first_top_level_segment(inner)
            return type_base_name(first_arg)
    return text


def _outer_type_argument(text: str, open_char: str, close_char: str) -> str | None:
    start = text.find(open_char)
    if start <= 0 or not text.endswith(close_char):
        return None
    depth = 0
    for idx, char in enumerate(text[start:], start=start):
        if char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                if idx != len(text) - 1:
                    return None
                return text[start + 1 : idx].strip()
    return None


def _first_top_level_segment(text: str) -> str:
    depth_angle = 0
    depth_square = 0
    for idx, char in enumerate(text):
        if char == "<":
            depth_angle += 1
        elif char == ">":
            depth_angle = max(0, depth_angle - 1)
        elif char == "[":
            depth_square += 1
        elif char == "]":
            depth_square = max(0, depth_square - 1)
        elif char == "," and depth_angle == 0 and depth_square == 0:
            return text[:idx].strip()
    return text.strip()


def _strip_prefix(text: str, prefix: str) -> str:
    if text.startswith(prefix):
        return text[len(prefix) :].strip()
    return text


def _strip_suffix(text: str, suffix: str) -> str:
    if text.endswith(suffix):
        return text[: -len(suffix)].strip()
    return text


def _strip_arrays(text: str) -> str:
    normalized = text
    while normalized.endswith("[]"):
        normalized = normalized[:-2].strip()
    return normalized

