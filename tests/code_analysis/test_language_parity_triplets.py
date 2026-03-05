# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
from pathlib import Path

from tests.code_analysis.parity_helpers import (
    assert_parity_expectations,
    build_snapshot,
    extension_for,
    language_specs,
)


def test_triplet_service_fixture_parity(tmp_path: Path) -> None:
    fixture_root = Path("tests/fixtures/parity/triplet_service")
    expected = json.loads((fixture_root / "expected.json").read_text(encoding="utf-8"))

    for rel_dir, fixture_name, analyzer, language in language_specs():
        source = (fixture_root / fixture_name).read_text(encoding="utf-8")
        ext = extension_for(language)
        rel_path = f"{rel_dir}/mod{ext}"
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")

        snapshot = build_snapshot(path, rel_path, language, source)
        module_name = analyzer.module_name(tmp_path, snapshot)
        analyzer.module_index = {module_name}
        result = analyzer.analyze(snapshot, module_name)
        assert_parity_expectations(result, module_name, expected)
