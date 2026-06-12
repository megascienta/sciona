# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from dataclasses import fields
import inspect

from sciona.runtime.reducers.metadata import (
    CATEGORY_ORDER,
    VALID_CATEGORIES,
)
from sciona.reducers.registry import ReducerEntry, get_reducers

def test_reducer_metadata_constants() -> None:
    assert CATEGORY_ORDER == ("orientation", "navigation", "coupling", "symbol", "diagnostic", "overlay", "source")
    assert set(CATEGORY_ORDER) == set(VALID_CATEGORIES)

def test_reducer_registry_exposes_category_only_metadata() -> None:
    reducers = get_reducers()
    assert reducers
    assert {field.name for field in fields(ReducerEntry)} == {
        "reducer_id",
        "category",
        "placeholder",
        "summary",
        "anomaly_detector",
        "module",
        "args",
        "requires",
    }
    for entry in reducers.values():
        assert entry.category in VALID_CATEGORIES
        assert entry.placeholder
        assert entry.module.__name__.startswith("sciona.reducers.")
        assert ".core." not in entry.module.__name__
        assert ".analytics." not in entry.module.__name__
        assert ".grounding." not in entry.module.__name__
        assert ".composites." not in entry.module.__name__

def test_reducer_args_document_every_render_parameter() -> None:
    reserved = {"snapshot_id", "conn", "repo_root"}
    for entry in get_reducers().values():
        render = getattr(entry.module, "render", None)
        assert render is not None, entry.reducer_id
        signature_params = {
            name
            for name, param in inspect.signature(render).parameters.items()
            if name not in reserved
            and param.kind is not inspect.Parameter.VAR_KEYWORD
        }
        documented = {arg.name for arg in entry.args}
        assert documented == signature_params, entry.reducer_id

def test_reducer_args_carry_descriptions_and_types() -> None:
    valid_types = {"str", "int", "bool"}
    for entry in get_reducers().values():
        for arg in entry.args:
            assert arg.type in valid_types, (entry.reducer_id, arg.name)
            assert arg.description.strip(), (entry.reducer_id, arg.name)
