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
    assert {"module", "class", "method", "function"}.issubset(node_types)
    assert not [edge for edge in result.edges if edge.edge_type == "CALLS"]
    method_edges = [edge for edge in result.edges if edge.edge_type == "DEFINES_METHOD"]
    assert method_edges and method_edges[0].src_node_type == "class"
    import_edges = [
        edge for edge in result.edges if edge.edge_type == "IMPORTS_DECLARED"
    ]
    assert not import_edges
    call_records = {
        record.qualified_name: set(record.callee_identifiers)
        for record in result.call_records
    }
    outer_name = f"{module_name}.outer"
    helper_name = f"{module_name}.helper"
    assert outer_name in call_records
    assert helper_name in call_records[outer_name]
    function_nodes = {
        node.qualified_name for node in result.nodes if node.node_type == "function"
    }
    assert f"{module_name}.inner" not in function_nodes
    assert f"{module_name}.inner" not in call_records


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
