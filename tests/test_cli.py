from __future__ import annotations

from pathlib import Path

import yaml

from llm_feature_workflow.cli import main


def test_init_creates_core_and_adapters(tmp_path: Path) -> None:
    project = tmp_path / "project"
    assert main(["init", str(project), "--agents", "agents", "zcode"]) == 0

    assert (project / ".workflow" / "workflow.yaml").is_file()
    assert (project / ".workflow" / "workflow.lock").is_file()
    assert (project / "commands" / "planejar-prd.md").is_file()
    assert (project / ".agents" / "rules" / "commands" / "planejar-prd.md").is_file()
    assert (project / ".zcode" / "commands" / "planejar-prd.md").is_file()
    assert (project / "templates" / "prd-template.md").is_file()
    assert (project / "MEMORY.md").is_file()


def test_configure_polyglot_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    assert main(["init", str(project)]) == 0
    result = main(
        [
            "configure",
            str(project),
            "--module",
            "api:backend=fastapi",
            "--module",
            "mobile:mobile=compose",
            "--service",
            "database=postgres",
            "--service",
            "cache=redis",
            "--uses",
            "api=database,cache",
            "--set",
            "api.test_command=uv run pytest",
            "--plugin",
            "kotlin-sql-ghost-fields",
            "--non-interactive",
        ]
    )
    assert result == 0

    config = yaml.safe_load((project / ".workflow" / "workflow.yaml").read_text(encoding="utf-8"))
    assert config["project"]["status"] == "configured"
    assert config["modules"]["api"]["resolved_profiles"] == ["python", "fastapi"]
    assert config["modules"]["mobile"]["resolved_profiles"] == ["kotlin", "android", "compose"]
    assert config["modules"]["api"]["uses"] == ["database", "cache"]
    assert (project / "scripts" / "find_ghost_fields.py").is_file()

    context = (project / ".workflow" / "generated" / "profile-context.md").read_text(
        encoding="utf-8"
    )
    assert "uv run pytest" in context
    assert "PostgreSQL" in context
    assert "Kotlin SQL Ghost Fields" in context


def test_configure_rejects_conflicting_frameworks(tmp_path: Path) -> None:
    project = tmp_path / "project"
    assert main(["init", str(project)]) == 0
    assert (
        main(
            [
                "configure",
                str(project),
                "--module",
                "api:backend=fastapi+django",
                "--non-interactive",
            ]
        )
        == 2
    )


def test_sync_and_doctor_are_idempotent(tmp_path: Path) -> None:
    project = tmp_path / "project"
    assert main(["init", str(project), "--agents", "agents"]) == 0
    assert main(["sync", str(project)]) == 0
    assert main(["sync", str(project)]) == 0
    assert main(["doctor", str(project)]) == 0


def test_doctor_detects_divergent_adapter(tmp_path: Path) -> None:
    project = tmp_path / "project"
    assert main(["init", str(project), "--agents", "agents"]) == 0
    mirrored = project / ".agents" / "rules" / "commands" / "planejar-prd.md"
    mirrored.write_text("alterado fora do gerador\n", encoding="utf-8")
    assert main(["doctor", str(project)]) == 1


def test_sync_removes_disabled_managed_plugin(tmp_path: Path) -> None:
    project = tmp_path / "project"
    assert main(["init", str(project)]) == 0
    assert (
        main(
            [
                "configure",
                str(project),
                "--module",
                "backend:backend=kotlin",
                "--plugin",
                "kotlin-sql-ghost-fields",
                "--non-interactive",
            ]
        )
        == 0
    )
    script = project / "scripts" / "find_ghost_fields.py"
    assert script.is_file()

    config_path = project / ".workflow" / "workflow.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["plugins"] = []
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    assert main(["sync", str(project)]) == 0
    assert not script.exists()
