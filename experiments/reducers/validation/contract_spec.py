# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from copy import deepcopy

# Validation policy surface (non-algorithmic). Strict call acceptance semantics
# are canonicalized in src/sciona/code_analysis/contracts/strict_call_contract.py.
_VALIDATION_CONTRACT = {
    "version": 1,
    "name": "sciona_structural_contract",
    "call_contract": {
        "require_callee_in_repo": True,
    },
    "imports": {
        "require_module_in_repo": True,
        "languages": {
            "python": {"resolver": "python_resolve"},
            "typescript": {"resolver": "typescript_normalize"},
            "java": {"resolver": "java_normalize"},
        },
    },
    "out_of_contract": {
        "standard_calls": [
            "len",
            "range",
            "print",
            "sorted",
            "sum",
            "min",
            "max",
            "str",
            "int",
            "float",
            "bool",
            "list",
            "dict",
            "set",
            "tuple",
            "enumerate",
            "zip",
            "map",
            "filter",
            "any",
            "all",
            "isinstance",
            "issubclass",
            "open",
            "getattr",
            "setattr",
            "hasattr",
            "dir",
            "abs",
            "round",
            "pow",
            "divmod",
            "complex",
            "bytes",
            "bytearray",
            "format",
            "hash",
            "id",
            "oct",
            "ord",
            "repr",
            "reversed",
            "slice",
            "sqrt",
            "sin",
            "cos",
            "tan",
            "log",
            "exp",
        ]
    },
}


def get_validation_contract() -> dict:
    return deepcopy(_VALIDATION_CONTRACT)


__all__ = ["get_validation_contract"]
