# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.api import errors
from sciona.runtime.errors import ConfigError, ScionaError


def test_api_errors_exports() -> None:
    assert errors.__all__ == ["ScionaError", "ConfigError"]
    assert errors.ScionaError is ScionaError
    assert errors.ConfigError is ConfigError
