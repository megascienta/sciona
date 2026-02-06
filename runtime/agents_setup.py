# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Loader for agents setup helpers defined in agents-setup.py."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


_IMPL_PATH = Path(__file__).with_name("agents-setup.py")


def _load_impl():
    spec = spec_from_file_location("sciona.runtime._agents_setup_impl", _IMPL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load agents setup module at {_IMPL_PATH}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_impl = _load_impl()

BEGIN_MARKER = _impl.BEGIN_MARKER
END_MARKER = _impl.END_MARKER
AGENTS_FILENAME = _impl.AGENTS_FILENAME
build_agents_block = _impl.build_agents_block
remove_agents_block = _impl.remove_agents_block
upsert_agents_file = _impl.upsert_agents_file

__all__ = [
    "AGENTS_FILENAME",
    "BEGIN_MARKER",
    "END_MARKER",
    "build_agents_block",
    "remove_agents_block",
    "upsert_agents_file",
]
