# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import pytest

from sciona.code_analysis.core import routing
from sciona.runtime.config.models import LanguageSettings
from sciona.runtime.errors import IngestionError


def test_select_analyzers_returns_enabled_instances() -> None:
    analyzers = routing.select_analyzers(
        {
            "python": LanguageSettings(name="python", enabled=True),
            "typescript": LanguageSettings(name="typescript", enabled=False),
        }
    )
    assert "python" in analyzers
    assert "typescript" not in analyzers


def test_select_analyzers_errors_for_missing_adapter(monkeypatch) -> None:
    monkeypatch.setattr(
        "sciona.code_analysis.core.extract.registry.get_analyzer",
        lambda _language: None,
    )
    with pytest.raises(IngestionError) as exc:
        routing.select_analyzers(
            {"fortran": LanguageSettings(name="fortran", enabled=True)}
        )
    assert "fortran" in str(exc.value)
    assert "sciona[fortran]" in str(exc.value)


def test_select_analyzers_errors_for_invalid_descriptor(monkeypatch) -> None:
    monkeypatch.setattr(
        "sciona.code_analysis.core.extract.interfaces.language_registry.assert_descriptor_compliant",
        lambda _language: (_ for _ in ()).throw(
            ValueError("Invalid language descriptor for 'python': missing module_namer")
        ),
    )
    with pytest.raises(IngestionError) as exc:
        routing.select_analyzers(
            {"python": LanguageSettings(name="python", enabled=True)}
        )
    assert "Invalid language descriptor for 'python'" in str(exc.value)
