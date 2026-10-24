"""Untrusted model output: validate before rendering or writing project files."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Rule(StrictModel):
    category: Literal["design", "security", "testing", "framework", "operations"]
    title: str = Field(min_length=3, max_length=150)
    instruction: str = Field(min_length=30, max_length=3000)
    rationale: str = Field(min_length=10, max_length=1000)
    example: str = Field(min_length=10, max_length=2000)
    exceptions: str = Field(min_length=3, max_length=1000)
    verification: str = Field(min_length=10, max_length=1000)


class Question(StrictModel):
    id: str = Field(pattern=r"^Q-[0-9]{2,}$")
    question: str = Field(min_length=10, max_length=1000)


class DomainEvidence(StrictModel):
    id: str = Field(pattern=r"^E-[0-9]{2,}$")
    source: str = Field(pattern=r"^(BRIEF|Q-[0-9]{2,}|REQUEST-[0-9]{2,})$")
    quote: str = Field(min_length=10, max_length=2000)
    finding: str = Field(min_length=10, max_length=2000)


class DomainPattern(StrictModel):
    pattern: Literal[
        "ubiquitous_language",
        "bounded_context",
        "entity",
        "value_object",
        "aggregate",
        "domain_service",
        "domain_event",
        "repository",
    ]
    candidate: str = Field(min_length=2, max_length=150)
    rationale: str = Field(min_length=20, max_length=2000)
    costs: str = Field(min_length=10, max_length=2000)
    evidence_ids: list[str] = Field(min_length=1, max_length=10)


class SimplerAlternative(StrictModel):
    approach: str = Field(min_length=10, max_length=2000)
    tradeoffs: str = Field(min_length=20, max_length=2000)


class DomainAssessment(StrictModel):
    module: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")
    scope: str = Field(min_length=2, max_length=150)
    recommendation: Literal[
        "simple_design", "strategic_ddd", "selective_ddd", "insufficient_context"
    ]
    rationale: str = Field(min_length=30, max_length=3000)
    evidence: list[DomainEvidence] = Field(max_length=12)
    suggested_patterns: list[DomainPattern] = Field(max_length=12)
    simpler_alternative: SimplerAlternative
    blocking_question_ids: list[str] = Field(max_length=12)

    @model_validator(mode="after")
    def justified_recommendation(self) -> DomainAssessment:
        ids = [e.id for e in self.evidence]
        if len(ids) != len(set(ids)):
            raise ValueError("evidências de domínio com IDs duplicados")
        for pattern in self.suggested_patterns:
            if set(pattern.evidence_ids) - set(ids):
                raise ValueError("padrão sem referência a evidência existente")
        patterns = {p.pattern for p in self.suggested_patterns}
        strategic = {"ubiquitous_language", "bounded_context"}
        if self.recommendation == "insufficient_context":
            if not self.blocking_question_ids or patterns:
                raise ValueError("contexto insuficiente exige perguntas e não autoriza padrões")
        else:
            if not self.evidence or self.blocking_question_ids:
                raise ValueError("recomendação conclusiva exige evidência e ausência de pendências")
            if self.recommendation == "simple_design" and patterns:
                raise ValueError("design simples não deve prescrever padrões DDD")
            if self.recommendation == "strategic_ddd" and (not patterns or patterns - strategic):
                raise ValueError("DDD estratégico não autoriza padrões táticos")
            if self.recommendation == "selective_ddd" and not patterns - strategic:
                raise ValueError("DDD seletivo exige padrão tático justificado")
        return self


def validate_assessment_links(
    assessments: list[DomainAssessment], modules: set[str], questions: set[str]
) -> None:
    scopes = [(a.module, a.scope.casefold()) for a in assessments]
    if len(scopes) != len(set(scopes)):
        raise ValueError("avaliação de domínio duplicada no mesmo escopo")
    covered = {a.module for a in assessments}
    if covered - modules or modules - covered:
        raise ValueError("avaliações de domínio precisam cobrir todos os módulos propostos")
    for assessment in assessments:
        if set(assessment.blocking_question_ids) - questions:
            raise ValueError("avaliação referencia pergunta bloqueante inexistente")


class Folder(StrictModel):
    path: str = Field(min_length=1, max_length=180)
    responsibility: str = Field(min_length=10, max_length=1000)

    @field_validator("path")
    @classmethod
    def relative_path(cls, value: str) -> str:
        if "\\" in value or value.startswith("/") or ":" in value:
            raise ValueError("use caminhos relativos com /")
        if any(part in {"..", ".git", ".env", ".workflow"} for part in value.split("/")):
            raise ValueError("caminho reservado ou fora do módulo")
        return value


class Gate(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]{1,60}$")
    command: str = Field(min_length=2, max_length=500)
    purpose: str = Field(min_length=10, max_length=1000)

    @field_validator("command")
    @classmethod
    def single_line(cls, value: str) -> str:
        if any(ord(char) < 32 for char in value):
            raise ValueError("comandos devem ter uma única linha sem controles")
        return value


Kind = Literal["backend", "frontend", "worker", "mobile", "library", "cli"]
Category = Literal["language", "framework", "runtime", "platform", "ui", "service"]


class ProfileDraft(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]{1,60}$")
    name: str = Field(min_length=2, max_length=120)
    category: Category
    requires: list[str] = Field(max_length=10)
    kinds: list[Kind] = Field(max_length=6)
    rules: list[Rule] = Field(min_length=2, max_length=15)
    edge_cases: list[str] = Field(min_length=2, max_length=20)


class ModuleDraft(StrictModel):
    name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")
    kind: Kind
    path: str = Field(min_length=1, max_length=180)
    profiles: list[str] = Field(min_length=1, max_length=12)
    uses: list[str] = Field(max_length=20)
    rules: list[Rule] = Field(min_length=3, max_length=25)
    folders: list[Folder] = Field(min_length=2, max_length=40)
    gates: list[Gate] = Field(min_length=1, max_length=15)

    @model_validator(mode="after")
    def essential_coverage(self) -> ModuleDraft:
        if not {"design", "security", "testing"}.issubset({rule.category for rule in self.rules}):
            raise ValueError("cada módulo precisa de regras de design, segurança e testes")
        return self


class ServiceDraft(StrictModel):
    name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")
    profile: str = Field(min_length=2, max_length=80)


class Proposal(StrictModel):
    architecture: str = Field(min_length=10, max_length=3000)
    rationale: str = Field(min_length=30, max_length=3000)
    assumptions: list[str] = Field(max_length=30)
    questions: list[Question] = Field(max_length=12)
    profiles: list[ProfileDraft] = Field(max_length=12)
    modules: list[ModuleDraft] = Field(max_length=12)
    services: list[ServiceDraft] = Field(max_length=20)
    domain_assessments: list[DomainAssessment] = Field(max_length=30)

    @model_validator(mode="after")
    def no_duplicates(self) -> Proposal:
        for label, values in (
            ("profiles", [p.id for p in self.profiles]),
            ("modules", [m.name for m in self.modules]),
            ("services", [s.name for s in self.services]),
            ("questions", [q.id for q in self.questions]),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"IDs duplicados em {label}")
        if not self.questions and not self.modules:
            raise ValueError("uma proposta sem perguntas deve conter módulos")
        validate_assessment_links(
            self.domain_assessments,
            {m.name for m in self.modules},
            {q.id for q in self.questions},
        )
        return self


def render_rules(rules: list[Rule]) -> str:
    return "\n\n".join(
        f"## {rule.title}\n\n{rule.instruction}\n\n"
        f"**Por quê:** {rule.rationale}\n\n**Exemplo:** {rule.example}\n\n"
        f"**Exceções:** {rule.exceptions}\n\n**Verificação:** {rule.verification}"
        for rule in rules
    )


def valid_model_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.:-]+", value):
        raise ValueError("informe o ID completo do modelo, como fornecedor/modelo")
    if value.split(":", 1)[0] in {"openrouter/auto", "openrouter/free"}:
        raise ValueError("escolha um modelo explícito, não um roteador automático")
    return value
