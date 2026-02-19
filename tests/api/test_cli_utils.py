# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import pytest
import typer

from sciona.cli.utils import parse_extra_args


def test_parse_extra_args_accepts_normalized_keys():
    args = ["--module-name=core.utils", "--verbose", "true"]
    parsed = parse_extra_args(args)
    assert parsed == {"module_name": "core.utils", "verbose": "true"}


def test_parse_extra_args_rejects_invalid_keys():
    with pytest.raises(typer.BadParameter):
        parse_extra_args(["--__class__=os.system"])


def test_parse_extra_args_rejects_dangerous_values():
    with pytest.raises(typer.BadParameter):
        parse_extra_args(["--module=core;rm -rf /"])
