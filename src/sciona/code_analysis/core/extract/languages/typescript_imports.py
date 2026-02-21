# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""TypeScript import extraction utilities."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Optional

from .....runtime import paths as runtime_paths
from ...module_naming import module_name_from_path
from ...normalize.model import FileSnapshot
from ..utils import find_nodes_of_type
from .shared import is_internal_module, repo_root_from_snapshot


def collect_typescript_imports(
    root,
    snapshot: FileSnapshot,
    module_name: str,
    *,
    module_index: set[str] | None,
) -> tuple[list[str], dict[str, str], dict[str, str]]:
    imports: list[str] = []
    import_aliases: dict[str, str] = {}
    member_aliases: dict[str, str] = {}
    repo_prefix = runtime_paths.repo_name_prefix(repo_root_from_snapshot(snapshot))
    nodes = list(find_nodes_of_type(root, "import_statement"))
    nodes.extend(list(find_nodes_of_type(root, "export_statement")))
    nodes.extend(list(find_nodes_of_type(root, "import_equals_declaration")))
    for node in nodes:
        fragment = snapshot.content[node.start_byte : node.end_byte].decode("utf-8")
        module_spec = extract_module_spec(fragment)
        if not module_spec:
            continue
        normalized = normalize_import(module_spec, snapshot)
        if not normalized or not is_internal_module(normalized, module_index):
            if module_index is not None and module_spec.strip().startswith("."):
                alt = normalize_relative_index(module_spec, snapshot)
                if alt and is_internal_module(alt, module_index):
                    normalized = alt
                else:
                    continue
            else:
                continue
        if repo_prefix and (
            normalized == repo_prefix or normalized.startswith(f"{repo_prefix}.")
        ):
            imports.append(normalized)
        else:
            imports.append(normalized)
        populate_ts_aliases(fragment, normalized, import_aliases, member_aliases)
    for node in find_nodes_of_type(root, "lexical_declaration"):
        fragment = snapshot.content[node.start_byte : node.end_byte].decode("utf-8")
        alias, module_spec = extract_require_assignment(fragment)
        if not alias or not module_spec:
            continue
        normalized = normalize_import(module_spec, snapshot)
        if not normalized or not is_internal_module(normalized, module_index):
            if module_index is not None and module_spec.strip().startswith("."):
                alt = normalize_relative_index(module_spec, snapshot)
                if alt and is_internal_module(alt, module_index):
                    normalized = alt
                else:
                    continue
            else:
                continue
        imports.append(normalized)
        import_aliases[alias] = normalized
    return imports, import_aliases, member_aliases


def extract_module_spec(fragment: str) -> Optional[str]:
    fragment = fragment.strip()
    if "from" in fragment:
        parts = fragment.split("from", 1)[1].strip()
        return string_literal(parts)
    if fragment.startswith("import"):
        remainder = fragment[len("import") :].strip()
        return string_literal(remainder)
    if fragment.startswith("export"):
        return string_literal(fragment)
    return None


def string_literal(text: str) -> Optional[str]:
    for quote in ("'", '"'):
        if quote in text:
            start = text.find(quote)
            end = text.find(quote, start + 1)
            if start >= 0 and end > start:
                return text[start + 1 : end]
    return None


def populate_ts_aliases(
    fragment: str,
    normalized: str,
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
) -> None:
    fragment = fragment.strip()
    if fragment.startswith("import") and "from" in fragment:
        head = fragment.split("from", 1)[0]
        if "{" in head and "}" in head:
            inner = head.split("{", 1)[1].rsplit("}", 1)[0]
            for part in inner.split(","):
                piece = part.strip()
                if not piece:
                    continue
                parts = piece.split(" as ", 1)
                name = parts[0].strip()
                alias = parts[1].strip() if len(parts) == 2 else None
                if name:
                    member_aliases[alias or name] = f"{normalized}.{name}"
        if "* as" in head:
            parts = head.split("* as", 1)[1].strip().split(",", 1)
            alias = parts[0].strip()
            if alias:
                import_aliases[alias] = normalized
        if "{" not in head and "*" not in head:
            parts = head.split()
            if len(parts) >= 2:
                alias = parts[1].strip().strip(",")
                if alias and alias not in {"from", "{"}:
                    import_aliases[alias] = normalized
    if fragment.startswith("import") and "require" in fragment and "=" in fragment:
        alias, _module = extract_require_assignment(fragment)
        if alias:
            import_aliases[alias] = normalized
    if fragment.startswith("export") and "from" in fragment and "{" in fragment:
        inner = fragment.split("{", 1)[1].rsplit("}", 1)[0]
        for part in inner.split(","):
            piece = part.strip()
            if not piece:
                continue
            parts = piece.split(" as ", 1)
            name = parts[0].strip()
            alias = parts[1].strip() if len(parts) == 2 else None
            if name:
                member_aliases[alias or name] = f"{normalized}.{name}"


def extract_require_assignment(fragment: str) -> tuple[str | None, str | None]:
    fragment = fragment.strip()
    if "require" not in fragment or "=" not in fragment:
        return None, None
    left, right = fragment.split("=", 1)
    alias = left.replace("const", "").replace("let", "").replace("var", "").strip()
    module = string_literal(right)
    return (alias or None, module)


def normalize_import(specifier: Optional[str], snapshot: FileSnapshot) -> Optional[str]:
    if not specifier:
        return None
    spec = specifier.strip().strip("'\"")
    if not spec:
        return None
    if spec.startswith("."):
        parent = PurePosixPath(snapshot.record.relative_path.parent.as_posix())
        normalized = normalize_relative_path(parent, PurePosixPath(spec))
        module_path = normalize_ts_path(normalized.as_posix())
        repo_root = repo_root_from_snapshot(snapshot)
        return module_name_from_path(
            repo_root,
            Path(module_path),
            strip_suffix=False,
            treat_init_as_package=False,
        )
    return spec.replace("/", ".")


def normalize_relative_index(specifier: str, snapshot: FileSnapshot) -> Optional[str]:
    spec = specifier.strip().strip("'\"")
    if not spec.startswith("."):
        return None
    parent = PurePosixPath(snapshot.record.relative_path.parent.as_posix())
    normalized = normalize_relative_path(parent, PurePosixPath(spec))
    index_path = normalized / "index"
    module_path = normalize_ts_path(index_path.as_posix())
    repo_root = repo_root_from_snapshot(snapshot)
    return module_name_from_path(
        repo_root,
        Path(module_path),
        strip_suffix=False,
        treat_init_as_package=False,
    )


def normalize_relative_path(base: PurePosixPath, relative: PurePosixPath) -> PurePosixPath:
    parts = list(base.parts)
    for part in relative.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return PurePosixPath(*parts)


def normalize_ts_path(path: str) -> str:
    name = path
    if name.endswith(".d.ts"):
        name = name[: -len(".d.ts")]
    elif name.endswith(".tsx"):
        name = name[: -len(".tsx")]
    elif name.endswith(".ts"):
        name = name[: -len(".ts")]
    elif name.endswith(".mjs"):
        name = name[: -len(".mjs")]
    elif name.endswith(".cjs"):
        name = name[: -len(".cjs")]
    elif name.endswith(".js"):
        name = name[: -len(".js")]
    return name
