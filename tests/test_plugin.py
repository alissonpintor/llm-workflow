from __future__ import annotations

import runpy
from importlib.resources import files
from pathlib import Path


def test_ghost_fields_plugin_finds_missing_column(tmp_path: Path) -> None:
    source = files("llm_feature_workflow").joinpath(
        "assets/plugins/kotlin-sql-ghost-fields/files/scripts/find_ghost_fields.py"
    )
    script = tmp_path / "plugin.py"
    script.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    namespace = runpy.run_path(str(script))
    target = tmp_path / "source"
    target.mkdir()
    (target / "Reader.kt").write_text(
        'val sql = "SELECT CODE FROM PRODUCT"\n'
        'val code = row["CODE"]\nval missing = row["MISSING"] ?: ""\n',
        encoding="utf-8",
    )
    candidates = namespace["collect"](target, False, None)
    assert len(candidates) == 1
    assert candidates[0].field == "MISSING"
    assert candidates[0].has_default
