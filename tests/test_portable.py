from __future__ import annotations

import re
from importlib.resources import files

import pytest

from llm_feature_workflow.cli import main
from llm_feature_workflow.config import load_config
from llm_feature_workflow.portable import STEP_CONTRACTS
from llm_feature_workflow.renderer import ADAPTERS


def test_default_installation_is_harness_neutral(tmp_path):
    assert main(["init", str(tmp_path)]) == 0
    assert load_config(tmp_path)["agents"]["targets"] == []
    for folder in (".agents", ".grok", ".zcode", ".opencode"):
        assert not (tmp_path / folder).exists()
    assert (tmp_path / ".workflow/START.md").is_file()
    assert ".workflow/START.md" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert main(["doctor", str(tmp_path)]) == 0


def test_core_has_no_harness_metadata_or_proprietary_invocations(tmp_path):
    assert main(["init", str(tmp_path)]) == 0
    core = files("llm_feature_workflow").joinpath("assets/core")
    for path in core.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert not text.startswith("---\n"), str(path)
        assert "trigger:" not in text
        assert not re.search(r"\.(grok|zcode|opencode|claude)/|@commands/", text)
    for group in ("commands", "rules", "templates"):
        for path in (tmp_path / ".workflow/generated" / group).glob("*.md"):
            assert not path.read_text(encoding="utf-8").startswith("---\n")


def test_every_step_has_contract_and_index_and_references_exist(tmp_path):
    assert main(["init", str(tmp_path)]) == 0
    commands = tmp_path / ".workflow/generated/commands"
    assert {p.stem for p in commands.glob("*.md")} == set(STEP_CONTRACTS)
    start = (tmp_path / ".workflow/START.md").read_text(encoding="utf-8")
    for path in commands.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        for heading in ("Entrada", "Saída", "Critério de conclusão", "Retomada"):
            assert f"## {heading}" in text
        assert f".workflow/generated/commands/{path.name}" in start
        assert (tmp_path / "commands" / path.name).read_text(encoding="utf-8") == text
    # All concrete canonical references resolve; the assessment is explicitly conditional.
    for relative in re.findall(r"`(\.workflow/[^`]+)`", start):
        if relative != ".workflow/generated/rules/domain-assessment.md":
            assert (tmp_path / relative).exists(), relative
    for limitation in ("outra sessão", "pendente", "autorrevisão", "checkpoint", "anexar"):
        assert limitation in start


@pytest.mark.parametrize("target", sorted(ADAPTERS))
def test_adapters_only_wrap_canonical_content(tmp_path, target):
    assert main(["init", str(tmp_path), "--agents", target]) == 0
    adapter = ADAPTERS[target]
    for group in ("commands", "rules"):
        for canonical in (tmp_path / ".workflow/generated" / group).glob("*.md"):
            expected = canonical.read_text(encoding="utf-8")
            actual = (tmp_path / adapter[group] / canonical.name).read_text(encoding="utf-8")
            assert actual.endswith(expected)
            if actual.startswith("---\n"):
                assert actual.split("---\n", 2)[2].lstrip("\n") == expected
    if target == "opencode":
        text = (tmp_path / adapter["commands"] / "criar-prd.md").read_text(encoding="utf-8")
        assert "description:" in text
        assert "trigger:" not in text


def test_switch_to_portable_preserves_unmanaged_files_and_legacy_configs(tmp_path):
    assert main(["init", str(tmp_path), "--agents", "grok", "zcode"]) == 0
    assert main(["upgrade", str(tmp_path)]) == 0
    assert load_config(tmp_path)["agents"]["targets"] == ["grok", "zcode"]
    unmanaged = tmp_path / ".grok/rules/team.md"
    unmanaged.write_text("Our own rule", encoding="utf-8")
    assert main(["configure", str(tmp_path), "--portable"]) == 0
    assert unmanaged.read_text(encoding="utf-8") == "Our own rule"
    assert not (tmp_path / ".grok/rules/common.md").exists()
    assert not (tmp_path / ".zcode/commands/criar-prd.md").exists()
    assert (tmp_path / ".workflow/generated/rules/common.md").is_file()
    assert main(["sync", str(tmp_path)]) == 0
    assert main(["doctor", str(tmp_path)]) == 0
    assert main(["configure", str(tmp_path), "--agents", "opencode"]) == 0
    assert (tmp_path / ".opencode/commands/criar-prd.md").is_file()


def test_portable_migration_blocks_if_adapter_was_modified(tmp_path):
    assert main(["init", str(tmp_path), "--agents", "grok"]) == 0
    path = tmp_path / ".grok/rules/common.md"
    path.write_text(path.read_text(encoding="utf-8") + "\nTeam changes", encoding="utf-8")
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert main(["configure", str(tmp_path), "--portable"]) == 2
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after
