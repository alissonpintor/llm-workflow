"""Harness-neutral step contracts; optional adapters add discovery metadata only."""

from __future__ import annotations

import yaml

STEP_CONTRACTS = {
    "definir-stack": (
        "Objetivo, restrições e configuração atual.",
        "Decisão de stack aprovada, ADR e configuração de módulos/serviços.",
        "Stack aprovada e doctor verificado; caso contrário, bloqueios explícitos.",
    ),
    "avaliar-dominio": (
        "Brief, discovery, processos e respostas do usuário com fontes identificadas.",
        "Avaliação por módulo/área em domain-assessment.md, com evidências e alternativas.",
        "Decisão aprovada pelo usuário ou perguntas bloqueantes; nunca inferir aprovação.",
    ),
    "criar-prd": (
        "Objetivo da funcionalidade, evidências e respostas do usuário.",
        "discovery.md e prd.md na pasta da funcionalidade.",
        "Requisitos e aceites rastreáveis, com dúvidas explicitamente registradas.",
    ),
    "revisar-prd": (
        "PRD, discovery e critérios de review em sessão independente.",
        "reviews/prd-review.md com achados, evidências e status.",
        "APROVADO ou REPROVADO com motivos; autorrevisão não é independente.",
    ),
    "criar-techspec": (
        "PRD aprovado, stack definida, avaliação de domínio e código/contexto acessível.",
        "techspec.md com decisões, riscos, testes e cobertura dos requisitos.",
        "Decisões justificadas ou perguntas técnicas bloqueantes explícitas.",
    ),
    "revisar-techspec": (
        "PRD, Tech Spec, avaliação de domínio e contexto técnico em sessão independente.",
        "reviews/techspec-review.md com achados e status.",
        "APROVADO ou REPROVADO com evidências e limites da inspeção.",
    ),
    "criar-uiux": (
        "PRD, plataformas e jornadas de usuário.",
        "uiux-spec.md ou justificativa de não aplicabilidade.",
        "Jornadas, estados, acessibilidade e aceites definidos quando aplicável.",
    ),
    "criar-tasks": (
        "PRD/Tech Spec aprovados e UI/UX quando aplicável.",
        "tasks.md e arquivos N_task.md com dependências e plano de verificação.",
        "Cobertura e ordem verificadas, decomposição aprovada pelo usuário.",
    ),
    "validar-planejamento": (
        "Documentos e reviews da funcionalidade.",
        "Resultado do lint, review semântico e estado READY ou bloqueado.",
        "READY somente com gates realmente verificados e sem perguntas bloqueantes.",
    ),
    "planejar-prd": (
        "Objetivo, pasta da funcionalidade e estado anterior, se houver.",
        "Planejamento completo, reviews e estado READY ou lista de bloqueios.",
        "Etapas concluídas com evidência, sem iniciar implementação de produto.",
    ),
    "executar-task": (
        "Plano READY, arquivo da task, TASK_BASE_SHA e escopo autorizado.",
        "Alterações e evidências, sem commit ou checkmark pela implementação.",
        "CANDIDATA_A_REVIEW, FALHOU ou SPEC_GAP, com testes executados/não executados.",
    ),
    "executar-review": (
        "Task, especificação, diff desde TASK_BASE_SHA e sessão independente.",
        "Review com achados, evidências e status da task.",
        "Decisão explícita; ausência de capacidade de review permanece bloqueio.",
    ),
    "executar-prd": (
        "Plano READY aprovado, PRD_BASE_SHA e autorização para as operações previstas.",
        "execution.md, evidências por task e aceite integrado.",
        "DONE somente após reviews, gates e aceite; caso contrário, checkpoint bloqueado.",
    ),
    "validar-entrega-prd": (
        "PRD_BASE_SHA original, requisitos, tasks aprovadas e alterações completas.",
        "acceptance.md com cobertura, resultados e decisão de aceite.",
        "Aceite explícito ou pendências bloqueantes; nunca inventar execução de gates.",
    ),
    "executar-bugfix": (
        "Sintoma, reprodução, contexto e escopo autorizado.",
        "Diagnóstico, teste de regressão, correção mínima e review independente.",
        "Causa confirmada e verificada ou hipóteses/bloqueios explicitamente separados.",
    ),
    "executar-qa": (
        "Jornadas, aceites, ambiente e permissões para testes.",
        "Relatório de resultados e reproduções, sem mudanças de produto.",
        "Casos classificados como passaram, falharam ou não executados.",
    ),
    "analisar-seguranca": (
        "Escopo, ameaças, perfis e evidências acessíveis.",
        "Relatório somente-leitura de riscos, evidências e limitações.",
        "Achados contextualizados; ações externas dependem de autorização separada.",
    ),
    "codigo-morto": (
        "Escopo e referências acessíveis do projeto.",
        "Relatório de candidatos, confirmações e falsos positivos, sem exclusões.",
        "Cada conclusão tem evidência e limitações; ferramentas estáticas não são prova final.",
    ),
}


def step_document(name: str, body: str) -> str:
    inputs, outputs, complete = STEP_CONTRACTS[name]
    return (
        body.rstrip() + f"\n\n## Entrada\n\n{inputs}\n\n## Saída\n\n{outputs}\n\n"
        f"## Critério de conclusão\n\n{complete}\n\n## Retomada\n\n"
        "Leia `.workflow/START.md` e os artefatos já existentes. Preserve decisões aprovadas, "
        "baselines originais e trabalho alheio. Registre etapa, caminhos, pendências, evidências "
        "e próxima ação em um checkpoint na pasta da funcionalidade. "
        "Se faltar capacidade, contexto ou autorização, pare e informe o bloqueio; "
        "não marque a etapa como concluída.\n"
    )


def adapter_document(target: str, group: str, content: str) -> str:
    """Keep adapter metadata out of canonical documents and preserve the exact prompt body."""
    if group == "commands":
        title = next(
            (line[2:] for line in content.splitlines() if line.startswith("# ")), "Workflow"
        )
        metadata = {"description": title}
        if target != "opencode":
            metadata["trigger"] = "manual"
    elif target in {"agents", "grok", "zcode"}:
        metadata = {"trigger": "always_on"}
    else:
        return content
    return (
        "---\n"
        + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False)
        + "---\n\n"
        + content
    )
