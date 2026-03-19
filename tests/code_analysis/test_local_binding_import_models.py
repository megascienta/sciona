# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from pathlib import Path

from sciona.code_analysis.core.extract.parsing.parser_bootstrap import (
    bootstrap_tree_sitter_parser,
)
from sciona.code_analysis.core.normalize_model import FileRecord, FileSnapshot
from sciona.code_analysis.languages.builtin.java.java_imports import (
    collect_java_import_model,
)
from sciona.code_analysis.languages.builtin.javascript.javascript_imports import (
    collect_javascript_import_model,
)
from sciona.code_analysis.languages.builtin.python.python_imports import (
    collect_python_import_model,
)
from sciona.code_analysis.languages.builtin.typescript.typescript_imports import (
    collect_typescript_import_model,
)
from sciona.code_analysis.languages.common.ir import alias_maps_from_binding_facts


def _snapshot(repo: Path, relative_path: str, language: str, content: str) -> FileSnapshot:
    path = repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return FileSnapshot(
        record=FileRecord(
            path=path,
            relative_path=Path(relative_path),
            language=language,
        ),
        file_id=relative_path,
        blob_sha="h",
        size=len(content.encode("utf-8")),
        line_count=content.count("\n") + 1,
        content=content.encode("utf-8"),
    )


def _parse_root(language: str, content: bytes):
    parser, _, _ = bootstrap_tree_sitter_parser(language)
    return parser.parse(content).root_node


def test_python_import_model_emits_shared_binding_facts(tmp_path) -> None:
    import sciona.code_analysis.languages.builtin.python.python_imports as python_imports

    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True, exist_ok=True)
    (repo / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "pkg" / "utils.py").write_text("", encoding="utf-8")
    (repo / "pkg" / "models.py").write_text("", encoding="utf-8")
    snapshot = _snapshot(
        repo,
        "pkg/mod.py",
        "python",
        "import utils\nfrom pkg.models import Widget as W, Gadget\n",
    )
    root = _parse_root("python", snapshot.content)
    original = python_imports.find_direct_children_query
    python_imports.find_direct_children_query = lambda root, language_name: root.children
    try:
        model = collect_python_import_model(
            root,
            snapshot,
            "repo.pkg.mod",
            module_index={"utils", "pkg.models"},
        )
    finally:
        python_imports.find_direct_children_query = original

    facts = {(fact.symbol, fact.target, fact.binding_kind) for fact in model.local_binding_facts}
    assert ("utils", "utils", "module_alias") in facts
    assert ("W", "pkg.models.Widget", "direct_import_symbol") in facts
    assert ("Gadget", "pkg.models.Gadget", "direct_import_symbol") in facts
    assert alias_maps_from_binding_facts(model.local_binding_facts) == (
        model.import_aliases,
        model.member_aliases,
    )


def test_javascript_import_model_emits_shared_binding_facts(tmp_path) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True, exist_ok=True)
    (repo / "src" / "dep.js").write_text("export const bar = 1;\n", encoding="utf-8")
    (repo / "src" / "dep2.js").write_text("export const value = 1;\n", encoding="utf-8")
    snapshot = _snapshot(
        repo,
        "src/mod.js",
        "javascript",
        "import foo, { bar as baz } from './dep';\nimport * as ns from './dep2';\n",
    )
    root = _parse_root("javascript", snapshot.content)
    model = collect_javascript_import_model(
        root,
        snapshot,
        "repo.src.mod",
        module_index={"repo.src.dep", "repo.src.dep2"},
    )

    facts = {(fact.symbol, fact.target, fact.binding_kind) for fact in model.local_binding_facts}
    assert ("foo", "repo.src.dep", "module_alias") in facts
    assert ("baz", "repo.src.dep.bar", "destructured_static_member") in facts
    assert ("ns", "repo.src.dep2", "namespace_alias") in facts
    assert alias_maps_from_binding_facts(model.local_binding_facts) == (
        model.import_aliases,
        model.member_aliases,
    )


def test_javascript_require_destructuring_emits_shared_binding_facts(tmp_path) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True, exist_ok=True)
    (repo / "src" / "dep.js").write_text("exports.bar = 1;\nexports.baz = 2;\n", encoding="utf-8")
    snapshot = _snapshot(
        repo,
        "src/mod.js",
        "javascript",
        "const { bar: qux, baz } = require('./dep');\n",
    )
    root = _parse_root("javascript", snapshot.content)
    model = collect_javascript_import_model(
        root,
        snapshot,
        "repo.src.mod",
        module_index={"repo.src.dep"},
    )
    facts = {(fact.symbol, fact.target, fact.binding_kind) for fact in model.local_binding_facts}
    assert ("qux", "repo.src.dep.bar", "destructured_static_member") in facts
    assert ("baz", "repo.src.dep.baz", "destructured_static_member") in facts


def test_typescript_import_model_emits_shared_binding_facts(tmp_path) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True, exist_ok=True)
    (repo / "src" / "dep.ts").write_text("export const bar = 1;\n", encoding="utf-8")
    (repo / "src" / "dep2.ts").write_text("export const value = 1;\n", encoding="utf-8")
    snapshot = _snapshot(
        repo,
        "src/mod.ts",
        "typescript",
        "import Foo, { bar as baz } from './dep';\nimport * as ns from './dep2';\n",
    )
    root = _parse_root("typescript", snapshot.content)
    model = collect_typescript_import_model(
        root,
        snapshot,
        "repo.src.mod",
        module_index={"repo.src.dep", "repo.src.dep2"},
    )

    facts = {(fact.symbol, fact.target, fact.binding_kind) for fact in model.local_binding_facts}
    assert ("Foo", "repo.src.dep", "module_alias") in facts
    assert ("baz", "repo.src.dep.bar", "destructured_static_member") in facts
    assert ("ns", "repo.src.dep2", "namespace_alias") in facts
    assert alias_maps_from_binding_facts(model.local_binding_facts) == (
        model.import_aliases,
        model.member_aliases,
    )


def test_typescript_require_destructuring_emits_shared_binding_facts(tmp_path) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True, exist_ok=True)
    (repo / "src" / "dep.ts").write_text("export const bar = 1;\nexport const baz = 2;\n", encoding="utf-8")
    snapshot = _snapshot(
        repo,
        "src/mod.ts",
        "typescript",
        "const { bar: qux, baz } = require('./dep');\n",
    )
    root = _parse_root("typescript", snapshot.content)
    model = collect_typescript_import_model(
        root,
        snapshot,
        "repo.src.mod",
        module_index={"repo.src.dep"},
    )
    facts = {(fact.symbol, fact.target, fact.binding_kind) for fact in model.local_binding_facts}
    assert ("qux", "repo.src.dep.bar", "destructured_static_member") in facts
    assert ("baz", "repo.src.dep.baz", "destructured_static_member") in facts


def test_java_import_model_emits_shared_binding_facts(tmp_path) -> None:
    repo = tmp_path / "repo"
    snapshot = _snapshot(
        repo,
        "src/main/java/com/acme/App.java",
        "java",
        "package com.acme;\nimport com.acme.foo.Widget;\nimport static com.acme.foo.Utils.make;\nclass App {}\n",
    )
    root = _parse_root("java", snapshot.content)
    model = collect_java_import_model(
        root,
        snapshot.content,
        "repo.src.main.java.com.acme.App",
        snapshot,
        module_prefix="repo.src.main.java",
        module_index={"repo.src.main.java.com.acme.foo.Widget", "repo.src.main.java.com.acme.foo.Utils"},
    )

    facts = {(fact.symbol, fact.target, fact.binding_kind) for fact in model.local_binding_facts}
    assert (
        "Widget",
        "repo.src.main.java.com.acme.foo.Widget",
        "constructor_or_classifier_import",
    ) in facts
    assert (
        "make",
        "repo.src.main.java.com.acme.foo.Utils.make",
        "static_import_member",
    ) in facts
    assert alias_maps_from_binding_facts(model.local_binding_facts) == (
        model.import_aliases,
        model.member_aliases,
    )
