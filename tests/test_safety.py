from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from llm_feature_workflow.cli import main
from llm_feature_workflow.config import WorkflowError, safe_path


@pytest.mark.parametrize("relative", ["../outside", "C:\\secret", "/etc/passwd", "a/../../x"])
def test_rejects_path_escape(tmp_path: Path, relative: str) -> None:
    with pytest.raises(WorkflowError):
        safe_path(tmp_path, relative)


def test_conflict_preflight_preserves_all_files_and_config(tmp_path: Path) -> None:
    assert main(["init", str(tmp_path)]) == 0
    config_path = tmp_path / ".workflow" / "workflow.yaml"
    before = config_path.read_bytes()
    command = tmp_path / "commands" / "executar-prd.md"
    command.write_text(
        command.read_text(encoding="utf-8") + "\nMinha customização\n", encoding="utf-8"
    )
    edited = command.read_bytes()
    assert (
        main(["configure", str(tmp_path), "--module", "api:backend=fastapi", "--non-interactive"])
        == 2
    )
    assert config_path.read_bytes() == before
    assert command.read_bytes() == edited
    assert not (tmp_path / ".workflow/generated/rules/profile-fastapi.md").exists()


def test_sync_preserves_project_memory_and_agents_content(tmp_path: Path) -> None:
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Regras próprias\nTexto da equipe.\n", encoding="utf-8")
    assert main(["init", str(tmp_path)]) == 0
    decision = tmp_path / "docs/decisions.md"
    decision.write_text("# Nossa decisão\nNão substituir.\n", encoding="utf-8")
    assert main(["sync", str(tmp_path)]) == 0
    assert main(["upgrade", str(tmp_path)]) == 0
    assert agents.read_text(encoding="utf-8").count("# Regras próprias") == 1
    assert decision.read_text(encoding="utf-8") == "# Nossa decisão\nNão substituir.\n"


def test_tampered_lock_cannot_remove_external_file(tmp_path: Path) -> None:
    project = tmp_path / "project"
    assert main(["init", str(project)]) == 0
    outside = tmp_path / "outside.md"
    outside.write_text("<!-- llm-workflow:managed -->\nimportant", encoding="utf-8")
    lock = project / ".workflow/workflow.lock"
    lock.write_text(yaml.safe_dump({"managed_files": {"../outside.md": "bad"}}), encoding="utf-8")
    assert main(["sync", str(project)]) == 2
    assert outside.is_file()


def test_yaml_edit_resolves_profiles_and_removes_obsolete_rules(tmp_path: Path) -> None:
    assert main(["init", str(tmp_path)]) == 0
    assert (
        main(["configure", str(tmp_path), "--module", "api:backend=fastapi", "--non-interactive"])
        == 0
    )
    path = tmp_path / ".workflow/workflow.yaml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    config["modules"]["api"]["requested_profiles"] = ["django"]
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    assert main(["sync", str(tmp_path)]) == 0
    assert not (tmp_path / ".workflow/generated/rules/profile-fastapi.md").exists()
    assert not (tmp_path / ".agents/rules/profile-fastapi.md").exists()
    assert (tmp_path / ".agents/rules/profile-django.md").is_file()


def test_unmanaged_collision_does_not_create_configuration(tmp_path: Path) -> None:
    commands = tmp_path / "commands"
    commands.mkdir()
    (commands / "executar-prd.md").write_text("Meu comando\n", encoding="utf-8")
    assert main(["init", str(tmp_path)]) == 2
    assert not (tmp_path / ".workflow/workflow.yaml").exists()


def test_command_frontmatter_stays_at_start(tmp_path: Path) -> None:
    assert main(["init", str(tmp_path)]) == 0
    text = (tmp_path / ".agents/rules/commands/criar-prd.md").read_text(encoding="utf-8")
    assert text.startswith("---\n")


def test_symlink_cannot_redirect_managed_writes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (project / "commands").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks não disponíveis neste ambiente")
    assert main(["init", str(project)]) == 2
    assert list(outside.iterdir()) == []
    assert not (project / ".workflow/workflow.yaml").exists()


def test_no_personal_paths_in_serialized_lock(tmp_path: Path) -> None:
    assert main(["init", str(tmp_path)]) == 0
    lock = (tmp_path / ".workflow/workflow.lock").read_text(encoding="utf-8")
    assert str(tmp_path) not in lock
    assert json.dumps(str(tmp_path))[1:-1] not in lock
