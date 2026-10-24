from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from llm_feature_workflow.ai_models import DomainAssessment, validate_assessment_links
from llm_feature_workflow.config import WorkflowError
from llm_feature_workflow.domain_assessment import (
    context_sources,
    render_assessments,
    validate_evidence,
)


@pytest.fixture
def assessment():
    return {
        "module": "api",
        "scope": "pedidos",
        "recommendation": "selective_ddd",
        "rationale": "O cancelamento precisa preservar invariantes sobre o estado do pedido.",
        "evidence": [
            {
                "id": "E-01",
                "source": "Q-01",
                "quote": "Pedidos enviados não podem ser cancelados.",
                "finding": "O ciclo de vida possui uma restrição de cancelamento.",
            }
        ],
        "suggested_patterns": [
            {
                "pattern": "aggregate",
                "candidate": "Pedido",
                "rationale": "Centralizar transições e invariantes de cancelamento do pedido.",
                "costs": "Maior disciplina de modelagem e testes de invariantes.",
                "evidence_ids": ["E-01"],
            }
        ],
        "simpler_alternative": {
            "approach": "Serviços de aplicação com regras explícitas",
            "tradeoffs": "Menor abstração, mas exige evitar regras duplicadas nas operações.",
        },
        "blocking_question_ids": [],
    }


def test_selective_ddd_has_traceable_pattern_cost_and_alternative(assessment):
    value = DomainAssessment.model_validate(assessment)
    sources = context_sources(
        "Gestão de pedidos", [], ["Q-01=Pedidos enviados não podem ser cancelados."]
    )
    validate_evidence([value], sources)
    report = render_assessments([value], approved=False)
    for expected in (
        "AGUARDA APROVAÇÃO",
        "aggregate",
        "Custos",
        "Alternativa mais simples",
        "Q-01",
        "não comprovam",
        "não exige microserviços",
    ):
        assert expected in report


@pytest.mark.parametrize("recommendation", ["simple_design", "strategic_ddd"])
def test_simple_and_strategic_choices_do_not_require_tactical_ddd(assessment, recommendation):
    assessment["recommendation"] = recommendation
    if recommendation == "simple_design":
        assessment["suggested_patterns"] = []
    else:
        assessment["suggested_patterns"][0]["pattern"] = "bounded_context"
    assert DomainAssessment.model_validate(assessment).recommendation == recommendation


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_evidence",
        "invented_ref",
        "duplicate_evidence",
        "simple_tactical",
        "strategic_tactical",
        "no_tactical",
        "no_cost",
        "no_alternative",
    ],
)
def test_unjustified_or_inconsistent_assessments_fail_schema(assessment, mutation):
    bad = copy.deepcopy(assessment)
    if mutation == "missing_evidence":
        bad["evidence"] = []
    elif mutation == "invented_ref":
        bad["suggested_patterns"][0]["evidence_ids"] = ["E-99"]
    elif mutation == "duplicate_evidence":
        bad["evidence"] *= 2
    elif mutation == "simple_tactical":
        bad["recommendation"] = "simple_design"
    elif mutation == "strategic_tactical":
        bad["recommendation"] = "strategic_ddd"
    elif mutation == "no_tactical":
        bad["suggested_patterns"][0]["pattern"] = "ubiquitous_language"
    elif mutation == "no_cost":
        del bad["suggested_patterns"][0]["costs"]
    else:
        del bad["simpler_alternative"]
    with pytest.raises(ValidationError):
        DomainAssessment.model_validate(bad)


def test_insufficient_context_requires_real_blocking_questions(assessment):
    assessment.update(
        recommendation="insufficient_context",
        evidence=[],
        suggested_patterns=[],
        blocking_question_ids=["Q-02"],
    )
    value = DomainAssessment.model_validate(assessment)
    validate_assessment_links([value], {"api"}, {"Q-02"})
    with pytest.raises(ValueError, match="inexistente"):
        validate_assessment_links([value], {"api"}, set())
    assessment["blocking_question_ids"] = []
    with pytest.raises(ValidationError):
        DomainAssessment.model_validate(assessment)


@pytest.mark.parametrize("sources", [{}, {"Q-01": "Usuário não disse o trecho alegado"}])
def test_invented_quotes_or_sources_are_rejected(assessment, sources):
    with pytest.raises(WorkflowError, match="citação literal"):
        validate_evidence([DomainAssessment.model_validate(assessment)], sources)


def test_assessment_must_cover_modules_without_duplicate_scopes(assessment):
    value = DomainAssessment.model_validate(assessment)
    with pytest.raises(ValueError, match="todos os módulos"):
        validate_assessment_links([value], {"api", "web"}, set())
    with pytest.raises(ValueError, match="duplicada"):
        validate_assessment_links([value, value], {"api"}, set())
