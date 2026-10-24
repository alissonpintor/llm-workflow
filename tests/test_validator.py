from __future__ import annotations

from pathlib import Path

from llm_feature_workflow.validator import validate_feature


def test_validate_complete_feature(tmp_path: Path) -> None:
    reviews = tmp_path / "reviews"
    reviews.mkdir()
    (tmp_path / "domain-assessment.md").write_text(
        "# Avaliação\n- Status: APROVADO\n- Recomendação: simple_design\n"
        "- Perguntas bloqueantes: 0\n## Escopo e Recomendação\nCRUD simples.\n"
        "## Evidências do Usuário\nBRIEF: Cadastro simples sem regras além dos campos.\n"
        "## Padrões, Benefícios e Custos\nNenhum padrão adicional.\n"
        "## Alternativa Mais Simples\nOrganização por funcionalidades.\n"
        "## Perguntas Abertas\nNenhuma.\n## Aprovação\nUsuário aprovou na revisão.\n",
        encoding="utf-8",
    )
    (tmp_path / "discovery.md").write_text(
        "# Descoberta\n## Evidências e Fontes\nEVD-01\n"
        "## Casos de Borda Candidatos\nEDGE-01\n## Perguntas Abertas\nNenhuma.\n",
        encoding="utf-8",
    )
    (tmp_path / "prd.md").write_text(
        "# PRD\n- Perguntas bloqueantes: 0\n## Problema e Evidências\n"
        "## Requisitos Funcionais\n- **RF-01:** comportamento\n"
        "## Requisitos Não Funcionais\n- **NFR-01:** qualidade\n"
        "## Casos de Borda e Exceções\n## Critérios de Aceite\n### AC-01\nCobre: RF-01\n",
        encoding="utf-8",
    )
    (tmp_path / "techspec.md").write_text(
        "# Tech\n- Perguntas técnicas bloqueantes: 0\n## Cobertura dos Requisitos\n"
        "| RF-01 | DEC-01 | TEST-01 |\n| NFR-01 | DEC-01 | TEST-01 |\n"
        "## Casos de Borda, Concorrência e Modos de Falha\n"
        "## Segurança e Privacidade\n## Estratégia de Testes\n| TEST-01 | Teste |\n"
        "## Decisões Técnicas\n### DEC-01\n",
        encoding="utf-8",
    )
    (tmp_path / "tasks.md").write_text(
        "# Tasks\n## Estado do Planejamento\n- UI/UX aplicável: NÃO\n"
        "- Responsável pelo release: gate final do PRD\n## Matriz de Tarefas\n"
        "RF-01 NFR-01\n## Tarefas\n- [ ] 1.0 Entrega\n## Cobertura Consolidada\n",
        encoding="utf-8",
    )
    (tmp_path / "1_task.md").write_text(
        "# Tarefa 1.0\n- Dependências: nenhuma\nRF-01 NFR-01 DEC-01 TEST-01\n"
        "## Plano de Verificação\n",
        encoding="utf-8",
    )
    (reviews / "prd-review.md").write_text("Status: APROVADO\n", encoding="utf-8")
    (reviews / "techspec-review.md").write_text("Status: APROVADO\n", encoding="utf-8")

    result = validate_feature(tmp_path)
    assert result.ok, result.errors


def test_validate_reports_missing_coverage(tmp_path: Path) -> None:
    (tmp_path / "discovery.md").write_text("# Descoberta\n", encoding="utf-8")
    (tmp_path / "prd.md").write_text("RF-01 AC-01\n", encoding="utf-8")
    (tmp_path / "techspec.md").write_text("DEC-01 TEST-01\n", encoding="utf-8")
    (tmp_path / "tasks.md").write_text("# vazio\n", encoding="utf-8")

    result = validate_feature(tmp_path)
    assert not result.ok
    assert any("requisitos sem cobertura" in error for error in result.errors)


def test_dependency_cycle_blocks_ready(tmp_path: Path) -> None:
    test_validate_complete_feature(tmp_path)
    task = tmp_path / "1_task.md"
    task.write_text(
        task.read_text(encoding="utf-8").replace("Dependências: nenhuma", "Dependências: 1.0"),
        encoding="utf-8",
    )
    assert any("ciclo" in error for error in validate_feature(tmp_path).errors)


def test_ui_spec_is_required_when_applicable(tmp_path: Path) -> None:
    test_validate_complete_feature(tmp_path)
    tasks = tmp_path / "tasks.md"
    tasks.write_text(
        tasks.read_text(encoding="utf-8").replace("UI/UX aplicável: NÃO", "UI/UX aplicável: SIM"),
        encoding="utf-8",
    )
    assert "uiux-spec.md obrigatório" in validate_feature(tmp_path).errors


def test_domain_approval_and_questions_block_ready(tmp_path: Path) -> None:
    test_validate_complete_feature(tmp_path)
    path = tmp_path / "domain-assessment.md"
    path.write_text(
        path.read_text(encoding="utf-8")
        .replace("Status: APROVADO", "Status: PROPOSTA")
        .replace("Perguntas bloqueantes: 0", "Perguntas bloqueantes: 1"),
        encoding="utf-8",
    )
    errors = validate_feature(tmp_path).errors
    assert "domain-assessment.md: aprovação humana pendente" in errors
    assert "domain-assessment.md: perguntas bloqueantes pendentes" in errors
