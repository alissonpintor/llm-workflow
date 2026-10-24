"""Trace domain recommendations to supplied user context, not model-invented evidence."""

from __future__ import annotations

from .ai_models import DomainAssessment
from .config import WorkflowError


def context_sources(brief: str, requests: list[str], answers: list[str]) -> dict[str, str]:
    sources = {"BRIEF": brief}
    sources.update({f"REQUEST-{i:02}": value for i, value in enumerate(requests, 1)})
    for answer in answers:
        question, _, text = answer.partition("=")
        sources[question] = text
    return sources


def validate_evidence(assessments: list[DomainAssessment], sources: dict[str, str]) -> None:
    for assessment in assessments:
        for evidence in assessment.evidence:
            source = sources.get(evidence.source)
            if source is None or evidence.quote not in source:
                raise WorkflowError(
                    "Avaliação de domínio sem citação literal do contexto fornecido. Nada aplicado."
                )


def render_assessments(assessments: list[DomainAssessment], *, approved: bool) -> str:
    state = "APROVADA PELO USUÁRIO" if approved else "PROPOSTA — AGUARDA APROVAÇÃO"
    lines = [
        "# Avaliação de domínio e adequação de DDD",
        "",
        f"Estado: {state}",
        "",
        "As citações demonstram rastreabilidade, não comprovam a interpretação da LLM. "
        "Não há pontuação automática. DDD não exige microserviços, CQRS ou event sourcing.",
    ]
    for assessment in assessments:
        lines.extend(
            [
                "",
                f"## {assessment.module} / {assessment.scope}",
                f"Recomendação: **{assessment.recommendation}**",
                assessment.rationale,
                "",
                "### Evidências do contexto do usuário",
            ]
        )
        for evidence in assessment.evidence:
            lines.extend(
                [
                    f"- {evidence.id} / {evidence.source}: {evidence.quote}",
                    f"  Interpretação proposta: {evidence.finding}",
                ]
            )
        lines.extend(["", "### Padrões seletivos, benefícios e custos"])
        for pattern in assessment.suggested_patterns:
            lines.extend(
                [
                    f"- {pattern.pattern}: {pattern.candidate}",
                    f"  Justificativa: {pattern.rationale}",
                    f"  Custos: {pattern.costs}",
                    f"  Evidências: {', '.join(pattern.evidence_ids)}",
                ]
            )
        if not assessment.suggested_patterns:
            lines.append("Nenhum padrão DDD prescrito.")
        lines.extend(
            [
                "",
                "### Alternativa mais simples",
                assessment.simpler_alternative.approach,
                assessment.simpler_alternative.tradeoffs,
            ]
        )
        if assessment.blocking_question_ids:
            lines.append("Perguntas bloqueantes: " + ", ".join(assessment.blocking_question_ids))
    return "\n".join(lines) + "\n"
