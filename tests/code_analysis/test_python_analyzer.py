# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.code_analysis.core.extract.languages.python import PythonAnalyzer
from sciona.code_analysis.core.normalize.model import FileRecord, FileSnapshot


def test_python_analyzer_extracts_structure(tmp_path):
    module = """
from .helpers import helper as helper_alias
from . import local_helper
import pkg.utils

class Foo:
    def bar(self):
        helper()

def outer():
    def inner():
        helper()
    inner()

def helper():
    pass
"""
    repo = tmp_path
    pkg = repo / "pkg"
    pkg.mkdir()
    file_path = pkg / "mod.py"
    file_path.write_text(module, encoding="utf-8")
    record = FileRecord(
        path=file_path,
        relative_path=Path("pkg/mod.py"),
        language="python",
    )
    snapshot = FileSnapshot(
        record=record,
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = PythonAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)
    node_types = {node.node_type for node in result.nodes}
    assert {"module", "type", "callable"}.issubset(node_types)
    assert not [edge for edge in result.edges if edge.edge_type == "CALLS"]
    method_edges = [edge for edge in result.edges if edge.edge_type == "LEXICALLY_CONTAINS"]
    assert method_edges
    import_edges = [
        edge for edge in result.edges if edge.edge_type == "IMPORTS_DECLARED"
    ]
    assert not import_edges
    call_records = {
        record.qualified_name: set(record.callee_identifiers)
        for record in result.call_records
    }
    outer_name = f"{module_name}.outer.inner"
    helper_name = f"{module_name}.helper"
    assert outer_name in call_records
    assert helper_name in call_records[outer_name]
    callable_nodes = {
        node.qualified_name for node in result.nodes if node.node_type == "callable"
    }
    assert f"{module_name}.outer.inner" in callable_nodes
    assert f"{module_name}.outer.inner" in call_records


def test_python_analyzer_resolves_instance_assignments_per_callable_scope(tmp_path):
    module = """
class Service:
    def run(self):
        pass

def top():
    s = Service()
    s.run()

def other():
    s = Service()
    s.run()
"""
    repo = tmp_path
    pkg = repo / "pkg"
    pkg.mkdir()
    file_path = pkg / "mod.py"
    file_path.write_text(module, encoding="utf-8")
    record = FileRecord(
        path=file_path,
        relative_path=Path("pkg/mod.py"),
        language="python",
    )
    snapshot = FileSnapshot(
        record=record,
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = PythonAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)
    call_records = {
        record.qualified_name: set(record.callee_identifiers)
        for record in result.call_records
    }
    service_run = f"{module_name}.Service.run"
    assert service_run in call_records[f"{module_name}.top"]
    assert service_run in call_records[f"{module_name}.other"]


def test_python_analyzer_resolves_from_imported_member_calls(tmp_path):
    helpers = """
def helper():
    return 1
"""
    module = """
from .helpers import helper

def top():
    helper()
"""
    repo = tmp_path
    pkg = repo / "pkg"
    pkg.mkdir()
    (pkg / "helpers.py").write_text(helpers, encoding="utf-8")
    file_path = pkg / "mod.py"
    file_path.write_text(module, encoding="utf-8")
    record = FileRecord(
        path=file_path,
        relative_path=Path("pkg/mod.py"),
        language="python",
    )
    snapshot = FileSnapshot(
        record=record,
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = PythonAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    helper_module = f"{module_name.rsplit('.', 1)[0]}.helpers"
    analyzer.module_index = {module_name, helper_module}
    result = analyzer.analyze(snapshot, module_name)
    call_records = {
        record.qualified_name: set(record.callee_identifiers)
        for record in result.call_records
    }
    assert f"{helper_module}.helper" in call_records[f"{module_name}.top"]


def test_python_analyzer_tracks_from_import_submodules(tmp_path):
    repo = tmp_path
    pkg = repo / "pkg"
    app = pkg / "app"
    pkg.mkdir()
    app.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "config.py").write_text("VALUE = 1\n", encoding="utf-8")
    (app / "__init__.py").write_text("", encoding="utf-8")
    (app / "a.py").write_text("A = 1\n", encoding="utf-8")
    (app / "b.py").write_text("B = 1\n", encoding="utf-8")
    file_path = pkg / "main.py"
    file_path.write_text("from . import config\nfrom .app import a, b\n", encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("pkg/main.py"),
            language="python",
        ),
        file_id="file",
        blob_sha="hash",
        size=file_path.stat().st_size,
        line_count=2,
        content=file_path.read_bytes(),
    )
    analyzer = PythonAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    package_prefix = module_name.rsplit(".", 1)[0]
    analyzer.module_index = {
        module_name,
        package_prefix,
        f"{package_prefix}.config",
        f"{package_prefix}.app",
        f"{package_prefix}.app.a",
        f"{package_prefix}.app.b",
    }
    result = analyzer.analyze(snapshot, module_name)
    imports = {
        edge.dst_qualified_name
        for edge in result.edges
        if edge.edge_type == "IMPORTS_DECLARED"
    }
    assert f"{package_prefix}.config" in imports
    assert f"{package_prefix}.app" in imports
    assert package_prefix not in imports


def test_python_analyzer_tracks_bare_relative_import_alias_submodule(tmp_path):
    repo = tmp_path
    pkg = repo / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "config.py").write_text("VALUE = 1\n", encoding="utf-8")
    file_path = pkg / "main.py"
    file_path.write_text("from . import config as cfg\n", encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("pkg/main.py"),
            language="python",
        ),
        file_id="file",
        blob_sha="hash",
        size=file_path.stat().st_size,
        line_count=1,
        content=file_path.read_bytes(),
    )
    analyzer = PythonAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    package_prefix = module_name.rsplit(".", 1)[0]
    analyzer.module_index = {
        module_name,
        package_prefix,
        f"{package_prefix}.config",
    }
    result = analyzer.analyze(snapshot, module_name)
    imports = {
        edge.dst_qualified_name
        for edge in result.edges
        if edge.edge_type == "IMPORTS_DECLARED"
    }
    assert f"{package_prefix}.config" in imports
    assert package_prefix not in imports


def test_python_analyzer_bare_relative_import_falls_back_to_package_when_not_module(tmp_path):
    repo = tmp_path
    pkg = repo / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    file_path = pkg / "main.py"
    file_path.write_text("from . import VERSION\n", encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("pkg/main.py"),
            language="python",
        ),
        file_id="file",
        blob_sha="hash",
        size=file_path.stat().st_size,
        line_count=1,
        content=file_path.read_bytes(),
    )
    analyzer = PythonAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    package_prefix = module_name.rsplit(".", 1)[0]
    analyzer.module_index = {
        module_name,
        package_prefix,
    }
    result = analyzer.analyze(snapshot, module_name)
    imports = {
        edge.dst_qualified_name
        for edge in result.edges
        if edge.edge_type == "IMPORTS_DECLARED"
    }
    assert package_prefix in imports


def test_python_analyzer_resolves_self_field_constructor_assignments(tmp_path):
    module = """
class Service:
    def run(self):
        pass

class Controller:
    def __init__(self):
        self.svc = Service()

    def handle(self):
        self.svc.run()
"""
    repo = tmp_path
    pkg = repo / "pkg"
    pkg.mkdir()
    file_path = pkg / "mod.py"
    file_path.write_text(module, encoding="utf-8")
    record = FileRecord(
        path=file_path,
        relative_path=Path("pkg/mod.py"),
        language="python",
    )
    snapshot = FileSnapshot(
        record=record,
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = PythonAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)
    call_records = {
        record.qualified_name: set(record.callee_identifiers)
        for record in result.call_records
    }
    assert f"{module_name}.Service.run" in call_records[f"{module_name}.Controller.handle"]


def test_python_analyzer_nested_class_and_async_decorated_callable_support(tmp_path):
    module = """
class Outer:
    class Inner:
        def ping(self):
            return 1

def deco(fn):
    return fn

@deco
async def handler():
    return 0
"""
    repo = tmp_path
    pkg = repo / "pkg"
    pkg.mkdir()
    file_path = pkg / "mod.py"
    file_path.write_text(module, encoding="utf-8")
    record = FileRecord(
        path=file_path,
        relative_path=Path("pkg/mod.py"),
        language="python",
    )
    snapshot = FileSnapshot(
        record=record,
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = PythonAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)
    qnames = {node.qualified_name for node in result.nodes}
    assert f"{module_name}.Outer" in qnames
    assert f"{module_name}.Outer.Inner" in qnames
    assert f"{module_name}.Outer.Inner.ping" in qnames
    assert f"{module_name}.handler" in qnames
    outer_node = next(node for node in result.nodes if node.qualified_name == f"{module_name}.Outer")
    assert (outer_node.metadata or {}).get("kind") == "class"
    inner_edge_types = {
        edge.edge_type
        for edge in result.edges
        if edge.src_qualified_name == f"{module_name}.Outer"
        and edge.dst_qualified_name == f"{module_name}.Outer.Inner"
    }
    assert {"LEXICALLY_CONTAINS"}.issubset(inner_edge_types)
    handler_node = next(node for node in result.nodes if node.qualified_name == f"{module_name}.handler")
    assert (handler_node.metadata or {}).get("kind") == "async_function"
    assert "decorators" not in (handler_node.metadata or {})
    assert not [node for node in result.nodes if node.node_type == "decorator"]
    assert not [edge for edge in result.edges if edge.edge_type == "DECORATED_BY"]


def test_python_analyzer_emits_async_method_inside_class_body(tmp_path):
    module = """
class Service:
    async def run(self):
        return 1
"""
    repo = tmp_path
    pkg = repo / "pkg"
    pkg.mkdir()
    file_path = pkg / "mod.py"
    file_path.write_text(module, encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("pkg/mod.py"),
            language="python",
        ),
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = PythonAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)
    qnames = {node.qualified_name for node in result.nodes}
    assert f"{module_name}.Service.run" in qnames
    method_node = next(
        node for node in result.nodes if node.qualified_name == f"{module_name}.Service.run"
    )
    assert method_node.node_type == "callable"
    assert (method_node.metadata or {}).get("kind") == "async_function"


def test_python_analyzer_resolves_typed_constructor_param_alias_for_self_field(tmp_path):
    module = """
class UserRepo:
    def find(self):
        pass

class Service:
    def __init__(self, repo: UserRepo):
        self.repo = repo

    def fetch(self):
        self.repo.find()
"""
    repo = tmp_path
    pkg = repo / "pkg"
    pkg.mkdir()
    file_path = pkg / "mod.py"
    file_path.write_text(module, encoding="utf-8")
    record = FileRecord(
        path=file_path,
        relative_path=Path("pkg/mod.py"),
        language="python",
    )
    snapshot = FileSnapshot(
        record=record,
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = PythonAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)
    call_records = {
        rec.qualified_name: set(rec.callee_identifiers) for rec in result.call_records
    }
    assert f"{module_name}.UserRepo.find" in call_records[f"{module_name}.Service.fetch"]


def test_python_analyzer_resolves_generic_typed_constructor_param_alias(tmp_path):
    module = """
from typing import Optional

class UserRepo:
    def find(self):
        pass

class Service:
    def __init__(self, repo: Optional[UserRepo]):
        self.repo = repo

    def fetch(self):
        self.repo.find()
"""
    repo = tmp_path
    pkg = repo / "pkg"
    pkg.mkdir()
    file_path = pkg / "mod.py"
    file_path.write_text(module, encoding="utf-8")
    record = FileRecord(
        path=file_path,
        relative_path=Path("pkg/mod.py"),
        language="python",
    )
    snapshot = FileSnapshot(
        record=record,
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = PythonAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)
    call_records = {
        rec.qualified_name: set(rec.callee_identifiers) for rec in result.call_records
    }
    assert f"{module_name}.UserRepo.find" in call_records[f"{module_name}.Service.fetch"]


def test_python_analyzer_emits_local_inheritance_edges(tmp_path):
    module = """
class Base:
    pass

class Child(Base):
    pass
"""
    repo = tmp_path
    pkg = repo / "pkg"
    pkg.mkdir()
    file_path = pkg / "mod.py"
    file_path.write_text(module, encoding="utf-8")
    record = FileRecord(
        path=file_path,
        relative_path=Path("pkg/mod.py"),
        language="python",
    )
    snapshot = FileSnapshot(
        record=record,
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = PythonAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)
    edge_types = {
        edge.edge_type
        for edge in result.edges
        if edge.src_qualified_name == f"{module_name}.Child"
        and edge.dst_qualified_name == f"{module_name}.Base"
    }
    assert "EXTENDS" in edge_types


def test_python_nested_function_calls_are_attributed_to_outer_callable(tmp_path):
    module = """
def outer():
    def inner():
        helper()
    inner()

def helper():
    pass
"""
    repo = tmp_path
    pkg = repo / "pkg"
    pkg.mkdir()
    file_path = pkg / "mod.py"
    file_path.write_text(module, encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("pkg/mod.py"),
            language="python",
        ),
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = PythonAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)
    call_records = {
        rec.qualified_name: set(rec.callee_identifiers) for rec in result.call_records
    }
    assert f"{module_name}.outer.inner" in call_records
    assert f"{module_name}.helper" in call_records[f"{module_name}.outer.inner"]


def test_python_analyzer_does_not_module_resolve_shadowed_param_call(tmp_path):
    module = """
def helper():
    pass

def outer(helper):
    helper()
"""
    repo = tmp_path
    pkg = repo / "pkg"
    pkg.mkdir()
    file_path = pkg / "mod.py"
    file_path.write_text(module, encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("pkg/mod.py"),
            language="python",
        ),
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = PythonAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)
    call_records = {
        rec.qualified_name: set(rec.callee_identifiers) for rec in result.call_records
    }
    assert f"{module_name}.helper" not in call_records.get(f"{module_name}.outer", set())


def test_python_callable_roles_cover_declared_nested_bound_constructor(tmp_path):
    module = """
class Service:
    def __init__(self):
        pass

    def run(self):
        pass

def outer():
    def inner():
        return 1
    bound = lambda: 2
    return inner() + bound()
"""
    repo = tmp_path
    pkg = repo / "pkg"
    pkg.mkdir()
    file_path = pkg / "mod.py"
    file_path.write_text(module, encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("pkg/mod.py"),
            language="python",
        ),
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = PythonAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)

    role_by_qname = {
        node.qualified_name: (node.metadata or {}).get("callable_role")
        for node in result.nodes
        if node.node_type == "callable"
    }
    assert role_by_qname[f"{module_name}.Service.__init__"] == "constructor"
    assert role_by_qname[f"{module_name}.Service.run"] == "declared"
    assert role_by_qname[f"{module_name}.outer"] == "declared"
    assert role_by_qname[f"{module_name}.outer.inner"] == "nested"
    assert role_by_qname[f"{module_name}.outer.bound"] == "bound"
