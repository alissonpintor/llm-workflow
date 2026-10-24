from __future__ import annotations

import copy
import getpass
import json
import warnings

import httpx
import pytest
from pydantic import ValidationError

from llm_feature_workflow import ai_cli, openrouter
from llm_feature_workflow.ai_models import Proposal, valid_model_id
from llm_feature_workflow.ai_workflow import (
    PROPOSAL_PATH,
    generate_proposal,
    read_record,
)
from llm_feature_workflow.cli import main
from llm_feature_workflow.config import WorkflowError, load_config, save_config
from llm_feature_workflow.openrouter import BASE_URL, OpenRouter
from llm_feature_workflow.profiles import load_profiles

TEST_KEY = "unit-test-credential-not-real"


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("Tests must never send real requests")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", fail)


@pytest.fixture
def draft():
    def rule(category):
        return {
            "category": category,
            "title": f"Regra concreta de {category}",
            "instruction": "Valide o contrato na fronteira e isole os efeitos externos do domínio.",
            "rationale": "Evita acoplamento de regras com detalhes externos.",
            "example": "Uma entrada inválida deve falhar antes de persistir.",
            "exceptions": "CRUD simples não exige agregados.",
            "verification": "Teste uma entrada inválida e confira a ausência de escrita.",
        }

    return {
        "architecture": "Monólito modular por feature",
        "rationale": "Um único módulo de API evita distribuição sem necessidade de negócio.",
        "assumptions": ["Escala inicial pequena"],
        "questions": [],
        "profiles": [],
        "services": [],
        "domain_assessments": [
            {
                "module": "api",
                "scope": "pedidos",
                "recommendation": "simple_design",
                "rationale": "O contexto descreve um cadastro simples de pedidos.",
                "evidence": [
                    {
                        "id": "E-01",
                        "source": "BRIEF",
                        "quote": "API de pedidos com",
                        "finding": "O contexto delimita uma funcionalidade de pedidos.",
                    }
                ],
                "suggested_patterns": [],
                "simpler_alternative": {
                    "approach": "Organização por feature com serviços de aplicação",
                    "tradeoffs": "Menos abstrações; reavaliar com novas invariantes.",
                },
                "blocking_question_ids": [],
            }
        ],
        "modules": [
            {
                "name": "api",
                "kind": "backend",
                "path": "backend",
                "profiles": ["fastapi"],
                "uses": [],
                "rules": [rule(category) for category in ("design", "security", "testing")],
                "folders": [
                    {
                        "path": "src/domain",
                        "responsibility": "Invariantes e regras independentes de I/O",
                    },
                    {
                        "path": "tests",
                        "responsibility": "Testes de comportamento e contratos públicos",
                    },
                ],
                "gates": [
                    {
                        "id": "tests",
                        "command": "uv run pytest",
                        "purpose": "Verificar contratos e testes negativos",
                    }
                ],
            }
        ],
    }


def envelope(draft):
    if draft["questions"]:
        result = {
            "kind": "questions",
            **{key: draft[key] for key in ("architecture", "rationale", "questions")},
        }
    else:
        result = copy.deepcopy({"kind": "proposal", **draft})
        for module in result["modules"]:
            rules = module["rules"]
            sections = {
                "additional": [
                    r for r in rules if r["category"] not in {"design", "security", "testing"}
                ]
            }
            for category in ("design", "security", "testing"):
                matches = [r for r in rules if r["category"] == category]
                if matches:
                    sections[category] = {k: v for k, v in matches[0].items() if k != "category"}
            module["rules"] = sections
    return {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": json.dumps({"result": result}, ensure_ascii=False),
                },
            }
        ],
        "usage": {
            "prompt_tokens": 40,
            "completion_tokens": 60,
            "cost": 0.1,
            "private_details": TEST_KEY,
        },
    }


def client_for(draft, seen=None):
    def handler(request):
        if seen is not None:
            seen.append(request)
        return httpx.Response(200, json=envelope(draft))

    return OpenRouter(api_key=TEST_KEY, transport=httpx.MockTransport(handler))


def generate(root, draft, **kwargs):
    return generate_proposal(
        root,
        model="vendor/model",
        brief="API de pedidos com invariantes de negócio",
        requests=kwargs.pop("requests", []),
        answers=kwargs.pop("answers", []),
        max_tokens=8000,
        client=kwargs.pop("client", client_for(draft)),
        **kwargs,
    )


def snapshot(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_structured_payload_and_private_usage(draft):
    seen = []
    proposal, metadata = client_for(draft, seen).generate(
        model="vendor/model",
        system="system",
        context={"brief": "safe"},
    )
    request = seen[0]
    body = json.loads(request.content)
    assert str(request.url) == BASE_URL + "/chat/completions"
    assert request.headers["Authorization"] == f"Bearer {TEST_KEY}"
    assert TEST_KEY not in request.content.decode()
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"]["additionalProperties"] is False
    assert body["provider"] == {
        "require_parameters": True,
        "allow_fallbacks": False,
        "data_collection": "deny",
    }
    assert body["stream"] is False
    assert "tools" not in body
    assert proposal.modules[0].name == "api"
    assert metadata == {
        "requested_model": "vendor/model",
        "prompt_tokens": 40,
        "completion_tokens": 60,
        "cost": 0.1,
    }


def test_catalog_is_public_filtered_and_robust():
    def handler(request):
        assert "Authorization" not in request.headers
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "vendor/structured",
                        "name": "Model",
                        "supported_parameters": ["structured_outputs"],
                    },
                    {"id": "vendor/old", "supported_parameters": ["response_format"]},
                    {"id": "vendor/malformed", "supported_parameters": None},
                    None,
                ]
            },
        )

    client = OpenRouter(api_key=TEST_KEY, transport=httpx.MockTransport(handler))
    assert client.models("STRUCT") == [{"id": "vendor/structured", "name": "Model"}]
    assert client.models("missing") == []


@pytest.mark.parametrize("status", [301, 307, 400, 401, 402, 429, 500, 503])
def test_errors_are_redacted_and_not_retried(status):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(status, text=TEST_KEY, headers={"Location": "https://example.org"})

    client = OpenRouter(api_key=TEST_KEY, transport=httpx.MockTransport(handler))
    with pytest.raises(WorkflowError) as error:
        client.generate(model="vendor/model", system="safe", context={})
    assert len(seen) == 1
    assert TEST_KEY not in str(error.value)
    assert str(status) in str(error.value)


def test_timeout_does_not_echo_exception_or_retry():
    seen = []

    def handler(request):
        seen.append(request)
        raise httpx.ReadTimeout(TEST_KEY)

    with pytest.raises(WorkflowError, match="pode ter sido cobrada") as error:
        OpenRouter(api_key=TEST_KEY, transport=httpx.MockTransport(handler)).generate(
            model="vendor/model", system="safe", context={}
        )
    assert TEST_KEY not in str(error.value)
    assert len(seen) == 1


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"choices": []},
        {"error": {"message": TEST_KEY}},
        [],
        {"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]},
        {"choices": [{"finish_reason": "stop", "message": {"content": "bad json"}}]},
        {"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}]},
        {"choices": [{"finish_reason": "stop", "message": {"content": None}}]},
    ],
)
def test_invalid_envelopes_and_schema_are_rejected(response):
    client = OpenRouter(
        api_key=TEST_KEY,
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response)),
    )
    with pytest.raises(WorkflowError) as error:
        client.generate(model="vendor/model", system="safe", context={})
    assert TEST_KEY not in str(error.value)


def test_refusal_and_credential_echo_are_discarded(draft):
    for refusal in (True, False):
        body = envelope(draft)
        if refusal:
            body["choices"][0]["message"]["refusal"] = "refused"
        else:
            draft["assumptions"] = [TEST_KEY]
            body = envelope(draft)
        client = OpenRouter(
            api_key=TEST_KEY,
            transport=httpx.MockTransport(lambda _, body=body: httpx.Response(200, json=body)),
        )
        with pytest.raises(WorkflowError):
            client.generate(model="vendor/model", system="safe", context={})


def test_no_credential_in_context_or_network_on_invalid_inputs(draft):
    seen = []
    client = client_for(draft, seen)
    for kwargs in (
        {"context": {"brief": TEST_KEY}},
        {"max_tokens": 0},
        {"model": "openrouter/auto"},
    ):
        options = {"model": "vendor/model", "system": "safe", "context": {}} | kwargs
        with pytest.raises(WorkflowError):
            client.generate(**options)
    assert not seen


def test_response_size_limit_and_invalid_json(monkeypatch):
    monkeypatch.setattr(openrouter, "MAX_RESPONSE_BYTES", 100)
    for content in (b"x" * 101, b"not json"):
        client = OpenRouter(
            transport=httpx.MockTransport(
                lambda _, content=content: httpx.Response(200, content=content)
            )
        )
        with pytest.raises(WorkflowError):
            client.models()


@pytest.mark.parametrize("model", ["no-slash", "a/b/c", "vendor/model\n", "openrouter/free"])
def test_model_id_validation(model):
    with pytest.raises(ValueError):
        valid_model_id(model)


def test_module_requires_design_security_testing_and_no_extra_fields(draft):
    for mutation in ("missing_category", "extra", "duplicate", "folder_escape"):
        bad = copy.deepcopy(draft)
        if mutation == "missing_category":
            bad["modules"][0]["rules"][0]["category"] = "framework"
        elif mutation == "extra":
            bad["execute"] = "ignored?"
        elif mutation == "duplicate":
            bad["modules"] *= 2
        else:
            bad["modules"][0]["folders"][0]["path"] = "../outside"
        with pytest.raises(ValidationError):
            Proposal.model_validate(bad)


def test_generate_preview_apply_sync_end_to_end(tmp_path, draft, monkeypatch, capsys):
    assert main(["init", str(tmp_path), "--agents", "agents"]) == 0
    before = snapshot(tmp_path)
    seen = []
    monkeypatch.setenv("OPENROUTER_API_KEY", TEST_KEY)
    monkeypatch.setattr(ai_cli, "OpenRouter", lambda **_: client_for(draft, seen))
    options = [
        "configure",
        str(tmp_path),
        "--ai",
        "--model",
        "vendor/model",
        "--brief",
        "API de pedidos com regras de negócio",
        "--non-interactive",
        "--module",
        "api:backend=fastapi",
        "--set",
        "api.package_manager=uv",
    ]
    assert main(options) == 2  # no egress without consent
    assert not seen
    assert snapshot(tmp_path) == before
    assert main(options + ["--allow-paid"]) == 0
    after = snapshot(tmp_path)
    assert {k: v for k, v in after.items() if k != PROPOSAL_PATH} == before
    assert TEST_KEY not in after[PROPOSAL_PATH].decode()
    assert main(["llm", "apply", str(tmp_path)]) == 2
    assert main(["llm", "preview", str(tmp_path)]) == 0
    report = capsys.readouterr().out
    assert "workflow.yaml (proposto)" in report
    assert "uv run pytest" in report
    assert main(["llm", "apply", str(tmp_path), "--approve"]) == 0
    assert load_config(tmp_path)["modules"]["api"]["settings"]["package_manager"] == "uv"
    assert (tmp_path / ".agents/rules/module-api.md").is_file()
    assert not (tmp_path / "backend").exists()  # no application scaffolding/execution
    assert main(["sync", str(tmp_path)]) == 0
    assert main(["doctor", str(tmp_path)]) == 0
    assert len(seen) == 1  # preview, apply and sync are offline


def test_allowlist_does_not_forward_existing_private_material(tmp_path, draft):
    assert main(["init", str(tmp_path)]) == 0
    assert (
        main(
            [
                "configure",
                str(tmp_path),
                "--module",
                "api:backend=fastapi",
                "--set",
                "api.private_value=do-not-send-this",
                "--non-interactive",
            ]
        )
        == 0
    )
    (tmp_path / ".env").write_text("SECRET=do-not-send-this", encoding="utf-8")
    (tmp_path / "private.py").write_text("do-not-send-this", encoding="utf-8")
    seen = []
    generate(tmp_path, draft, client=client_for(draft, seen))
    payload = seen[0].content.decode()
    assert "do-not-send-this" not in payload
    assert "private_value" not in payload
    assert "private.py" not in payload
    assert str(tmp_path) not in payload


def test_resume_includes_questions_answers_and_original_requests(tmp_path, draft):
    assert main(["init", str(tmp_path)]) == 0
    pending = copy.deepcopy(draft)
    pending["questions"] = [{"id": "Q-01", "question": "Qual o modelo de autorização por pedido?"}]
    generate(tmp_path, pending, requests=["module api:backend=fastapi"])
    before = snapshot(tmp_path)
    assert main(["llm", "apply", str(tmp_path), "--approve"]) == 2
    assert snapshot(tmp_path) == before
    seen = []
    generate(tmp_path, draft, answers=["Q-01=Somente proprietário"], client=client_for(draft, seen))
    context = json.loads(json.loads(seen[0].content)["messages"][1]["content"])
    assert context["previous_questions"] == pending["questions"]
    assert context["answers"] == ["Q-01=Somente proprietário"]
    assert context["requests"] == ["module api:backend=fastapi"]
    assert read_record(tmp_path).requests == context["requests"]


def test_stale_proposal_and_missing_modules_fail_without_writes(tmp_path, draft):
    assert main(["init", str(tmp_path)]) == 0
    generate(tmp_path, draft)
    config = load_config(tmp_path)
    config["project"]["architecture"] = "Changed decision"
    save_config(tmp_path, config)
    before = snapshot(tmp_path)
    assert main(["llm", "apply", str(tmp_path), "--approve"]) == 2
    assert snapshot(tmp_path) == before
    assert (
        main(["configure", str(tmp_path), "--module", "other:backend=django", "--non-interactive"])
        == 0
    )
    with pytest.raises(WorkflowError, match="todos os módulos"):
        generate(tmp_path, draft)


def test_explicit_stack_cannot_be_silently_replaced(tmp_path, draft):
    assert main(["init", str(tmp_path)]) == 0
    with pytest.raises(WorkflowError, match="não respeita --module"):
        generate(tmp_path, draft, requests=["module api:backend=django"])
    assert not (tmp_path / PROPOSAL_PATH).exists()


def test_local_profiles_review_apply_and_editable_sources(tmp_path, draft, capsys):
    assert main(["init", str(tmp_path)]) == 0
    draft["profiles"] = [
        {
            "id": "custom-python-web",
            "name": "Custom Python Web",
            "category": "framework",
            "requires": ["python"],
            "kinds": ["backend"],
            "rules": draft["modules"][0]["rules"],
            "edge_cases": ["Falha na persistência", "Autorização negada"],
        }
    ]
    draft["modules"][0]["profiles"] = ["custom-python-web"]
    generate(tmp_path, draft)
    assert main(["llm", "preview", str(tmp_path)]) == 0
    report = capsys.readouterr().out
    assert ".workflow/profiles/custom-python-web/profile.yaml" in report
    assert "Custom Python Web" in report
    assert main(["llm", "apply", str(tmp_path), "--approve"]) == 0
    assert "custom-python-web" in load_profiles(tmp_path)
    source = tmp_path / ".workflow/profiles/custom-python-web/profile.yaml"
    source.write_text(
        source.read_text(encoding="utf-8") + "\n# Customização local\n", encoding="utf-8"
    )
    assert main(["sync", str(tmp_path)]) == 0
    assert main(["doctor", str(tmp_path)]) == 0
    assert "Customização local" in source.read_text(encoding="utf-8")


def test_apply_conflict_preserves_everything(tmp_path, draft):
    assert main(["init", str(tmp_path)]) == 0
    generate(tmp_path, draft)
    (tmp_path / "commands/criar-prd.md").write_text("Custom command", encoding="utf-8")
    before = snapshot(tmp_path)
    assert main(["llm", "apply", str(tmp_path), "--approve"]) == 2
    assert snapshot(tmp_path) == before


def test_setup_is_offline_and_never_saves_key(tmp_path, monkeypatch):
    assert main(["init", str(tmp_path)]) == 0
    monkeypatch.setenv("OPENROUTER_API_KEY", TEST_KEY)
    assert main(["llm", "setup", str(tmp_path), "--model", "vendor/model"]) == 0
    assert load_config(tmp_path)["ai"] == {
        "provider": "openrouter",
        "model": "vendor/model",
        "max_output_tokens": 8000,
    }
    assert all(TEST_KEY.encode() not in value for value in snapshot(tmp_path).values())
    assert (
        main(["llm", "setup", str(tmp_path), "--model", "vendor/model", "--max-tokens", "0"]) == 2
    )
    assert main(["doctor", str(tmp_path)]) == 0


def test_unicode_escaped_credential_cannot_be_persisted(tmp_path, draft):
    assert main(["init", str(tmp_path)]) == 0
    draft["assumptions"] = [TEST_KEY]
    response = envelope(draft)
    response["choices"][0]["message"]["content"] = response["choices"][0]["message"][
        "content"
    ].replace(TEST_KEY, "\\u0075" + TEST_KEY[1:])
    client = OpenRouter(
        api_key=TEST_KEY,
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response)),
    )
    with pytest.raises(WorkflowError, match="credencial"):
        generate(tmp_path, draft, client=client)
    assert not (tmp_path / PROPOSAL_PATH).exists()


@pytest.mark.parametrize("answers", [["Q-99=texto"], ["Q-01="], ["Q-01=texto", "Q-01=duplicado"]])
def test_invalid_answers_do_not_send_or_overwrite(tmp_path, draft, answers):
    assert main(["init", str(tmp_path)]) == 0
    draft["questions"] = [{"id": "Q-01", "question": "Qual o modelo de autorização por pedido?"}]
    generate(tmp_path, draft)
    before = snapshot(tmp_path)
    seen = []
    with pytest.raises(WorkflowError, match="pergunta pendente"):
        generate(tmp_path, draft, answers=answers, client=client_for(draft, seen))
    assert not seen
    assert snapshot(tmp_path) == before


def test_unknown_proposal_file_is_never_overwritten(tmp_path, draft):
    assert main(["init", str(tmp_path)]) == 0
    proposal = tmp_path / PROPOSAL_PATH
    proposal.parent.mkdir(parents=True)
    proposal.write_text("My own file", encoding="utf-8")
    before = snapshot(tmp_path)
    seen = []
    with pytest.raises(WorkflowError, match="Proposta inválida"):
        generate(tmp_path, draft, client=client_for(draft, seen))
    assert not seen
    assert snapshot(tmp_path) == before


def test_local_profile_cannot_replace_builtin_or_have_cycles(tmp_path):
    assert main(["init", str(tmp_path)]) == 0
    source = tmp_path / ".workflow/profiles/python/profile.yaml"
    source.parent.mkdir(parents=True)
    source.write_text("id: python\ncategory: language\n", encoding="utf-8")
    assert main(["profiles", str(tmp_path)]) == 2
    # Preserve the conflicting source and test a separate project for a cycle.
    other = tmp_path / "other"
    assert main(["init", str(other)]) == 0
    source = other / ".workflow/profiles/local-cycle/profile.yaml"
    source.parent.mkdir(parents=True)
    source.write_text(
        "id: local-cycle\ncategory: language\nrequires: [local-cycle]\n", encoding="utf-8"
    )
    assert (
        main(["configure", str(other), "--module", "api:backend=local-cycle", "--non-interactive"])
        == 2
    )


def test_changed_local_profile_invalidates_pending_proposal(tmp_path, draft):
    assert main(["init", str(tmp_path)]) == 0
    source = tmp_path / ".workflow/profiles/local-language/profile.yaml"
    source.parent.mkdir(parents=True)
    source.write_text("id: local-language\ncategory: language\nrule: Old rule\n", encoding="utf-8")
    generate(tmp_path, draft)
    source.write_text("id: local-language\ncategory: language\nrule: New rule\n", encoding="utf-8")
    before = snapshot(tmp_path)
    assert main(["llm", "apply", str(tmp_path), "--approve"]) == 2
    assert snapshot(tmp_path) == before


def test_terminal_controls_are_not_rendered(tmp_path, draft, capsys):
    assert main(["init", str(tmp_path)]) == 0
    draft["assumptions"] = ["Remote \x1b[31m control"]
    generate(tmp_path, draft)
    assert main(["llm", "preview", str(tmp_path)]) == 0
    assert "\x1b" not in capsys.readouterr().out


def test_key_prompt_refuses_plaintext_fallback(tmp_path, monkeypatch):
    assert main(["init", str(tmp_path)]) == 0
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(ai_cli.sys.stdin, "isatty", lambda: True)

    def unsafe_prompt(_):
        warnings.warn("No echo control", getpass.GetPassWarning, stacklevel=1)
        pytest.fail("Must not fall back to visible credential input")

    monkeypatch.setattr(ai_cli.getpass, "getpass", unsafe_prompt)
    before = snapshot(tmp_path)
    assert (
        main(
            [
                "configure",
                str(tmp_path),
                "--ai",
                "--model",
                "vendor/model",
                "--brief",
                "API de pedidos com validações",
                "--allow-paid",
            ]
        )
        == 2
    )
    assert snapshot(tmp_path) == before


def test_ddd_assessment_appears_in_preview_and_approved_rules(tmp_path, draft, capsys):
    assert main(["init", str(tmp_path)]) == 0
    generate(tmp_path, draft)
    assert main(["llm", "preview", str(tmp_path)]) == 0
    report = capsys.readouterr().out
    assert "Avaliação de domínio" in report
    assert "AGUARDA APROVAÇÃO" in report
    assert "simple_design" in report
    assert main(["llm", "apply", str(tmp_path), "--approve"]) == 0
    path = tmp_path / ".workflow/generated/rules/domain-assessment.md"
    assert "APROVADA PELO USUÁRIO" in path.read_text(encoding="utf-8")
    assert load_config(tmp_path)["domain_assessments"][0]["evidence"][0]["source"] == "BRIEF"
    assert main(["sync", str(tmp_path)]) == 0
    assert main(["doctor", str(tmp_path)]) == 0


def test_fabricated_domain_evidence_never_saves_proposal(tmp_path, draft):
    assert main(["init", str(tmp_path)]) == 0
    draft["domain_assessments"][0]["evidence"][0]["quote"] = "Invented user statement"
    before = snapshot(tmp_path)
    with pytest.raises(WorkflowError, match="citação literal"):
        generate(tmp_path, draft)
    assert snapshot(tmp_path) == before


def test_domain_questions_block_then_resume_with_cited_answers(tmp_path, draft):
    assert main(["init", str(tmp_path)]) == 0
    pending = copy.deepcopy(draft)
    pending["questions"] = [{"id": "Q-01", "question": "Quais regras impedem cancelar um pedido?"}]
    pending["domain_assessments"][0].update(
        recommendation="insufficient_context", evidence=[], blocking_question_ids=["Q-01"]
    )
    generate(tmp_path, pending)
    assert main(["llm", "apply", str(tmp_path), "--approve"]) == 2
    decision = draft["domain_assessments"][0]
    decision["evidence"][0].update(source="Q-01", quote="Cadastro sem regras além dos campos.")
    seen = []
    generate(
        tmp_path,
        draft,
        answers=["Q-01=Cadastro sem regras além dos campos."],
        client=client_for(draft, seen),
    )
    context = json.loads(json.loads(seen[0].content)["messages"][1]["content"])
    assert context["domain_sources"]["Q-01"] == "Cadastro sem regras além dos campos."
    assert main(["llm", "apply", str(tmp_path), "--approve"]) == 0


def test_truncation_reports_token_limit_without_exposing_output(draft):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {"content": "partial private output"},
                    }
                ]
            },
        )

    client = OpenRouter(api_key=TEST_KEY, transport=httpx.MockTransport(handler))
    with pytest.raises(WorkflowError) as error:
        client.generate(model="vendor/model", system="safe", context={}, max_tokens=8000)
    message = str(error.value)
    assert "truncada" in message
    assert "8000" in message
    assert "raciocínio" in message
    assert "partial private output" not in message
    assert len(seen) == 1


def test_schema_diagnostics_identify_fields_without_echoing_values(draft):
    del draft["modules"][0]["rules"][0]["instruction"]
    draft["private-extra-field"] = "private-value-do-not-display"
    client = client_for(draft)
    with pytest.raises(WorkflowError) as error:
        client.generate(model="vendor/model", system="safe", context={})
    message = str(error.value)
    assert "modules[0].rules.design.instruction" in message
    assert "obrigatório" in message
    assert "private-extra-field" not in message
    assert "private-value-do-not-display" not in message


@pytest.mark.parametrize(
    "choice,expected",
    [
        ({"finish_reason": "stop", "message": {"refusal": "private refusal reason"}}, "recusada"),
        ({"finish_reason": "content_filter", "message": {"content": None}}, "recusada"),
        (
            {
                "finish_reason": "stop",
                "message": {"content": None, "reasoning": "private reasoning"},
            },
            "raciocínio",
        ),
        (
            {"finish_reason": "stop", "message": {"content": "not JSON private text"}},
            "JSON inválido",
        ),
    ],
)
def test_failure_categories_are_distinct_and_redacted(choice, expected):
    client = OpenRouter(
        api_key=TEST_KEY,
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"choices": [choice]})),
    )
    with pytest.raises(WorkflowError) as error:
        client.generate(model="vendor/model", system="safe", context={})
    assert expected in str(error.value)
    assert "private" not in str(error.value)


def test_semantic_schema_errors_explain_category_requirements(draft):
    draft["modules"][0]["rules"][0]["category"] = "framework"
    with pytest.raises(WorkflowError) as error:
        client_for(draft).generate(model="vendor/model", system="safe", context={})
    assert "modules[0]" in str(error.value)
    assert "rules.design" in str(error.value)
    assert "obrigatório" in str(error.value)


def test_truncation_only_shows_allowlisted_usage_counters():
    response = {
        "choices": [{"finish_reason": "length", "message": {"content": None}}],
        "usage": {
            "completion_tokens": 8000,
            "private_field": TEST_KEY,
            "completion_tokens_details": {"reasoning_tokens": 7999, "private": TEST_KEY},
        },
    }
    client = OpenRouter(
        api_key=TEST_KEY,
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response)),
    )
    with pytest.raises(WorkflowError) as error:
        client.generate(model="vendor/model", system="safe", context={})
    assert "saída=8000" in str(error.value)
    assert "raciocínio=7999" in str(error.value)
    assert TEST_KEY not in str(error.value)


def test_copied_example_brief_is_rejected_before_consent_or_network(tmp_path, monkeypatch, capsys):
    assert main(["init", str(tmp_path)]) == 0
    monkeypatch.setenv("OPENROUTER_API_KEY", TEST_KEY)
    before = snapshot(tmp_path)
    assert (
        main(
            [
                "configure",
                str(tmp_path),
                "--ai",
                "--model",
                "vendor/model",
                "--brief",
                "Descrição do projeto, regras de negócio e stack",
                "--non-interactive",
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert "texto de exemplo" in captured.err
    assert "Destino:" not in captured.out
    assert snapshot(tmp_path) == before


def test_setup_reports_env_presence_without_reading_dotenv(tmp_path, monkeypatch, capsys):
    assert main(["init", str(tmp_path)]) == 0
    (tmp_path / ".env").write_text(f"OPENROUTER_API_KEY={TEST_KEY}\n", encoding="utf-8")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    capsys.readouterr()
    assert main(["llm", "setup", str(tmp_path), "--model", "vendor/model"]) == 0
    output = capsys.readouterr().out
    assert "não está visível neste processo" in output
    assert ".env não são carregados" in output
    monkeypatch.setenv("OPENROUTER_API_KEY", TEST_KEY)
    assert main(["llm", "setup", str(tmp_path), "--model", "vendor/model"]) == 0
    output = capsys.readouterr().out
    assert "detectada neste processo" in output
    assert "validade não verificada" in output
    assert TEST_KEY not in output


def test_question_only_response_remains_valid_and_does_not_apply(tmp_path, draft):
    assert main(["init", str(tmp_path)]) == 0
    before = snapshot(tmp_path)
    draft.update(
        modules=[],
        domain_assessments=[],
        questions=[
            {"id": "Q-01", "question": "Quais são os processos de negócio e a stack desejada?"}
        ],
    )
    record = generate(tmp_path, draft)
    assert record.proposal.questions
    after = snapshot(tmp_path)
    assert {k: v for k, v in after.items() if k != PROPOSAL_PATH} == before
    assert main(["llm", "apply", str(tmp_path), "--approve"]) == 2


def test_clarification_wire_response_cannot_require_speculative_modules():
    result = {
        "kind": "questions",
        "architecture": "Decisão pendente de contexto do negócio",
        "rationale": "Precisamos conhecer os processos antes de gerar regras ou estruturas.",
        "questions": [{"id": "Q-01", "question": "Quais são os processos e regras deste produto?"}],
    }
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": json.dumps({"result": result})},
                    }
                ]
            },
        )

    client = OpenRouter(api_key=TEST_KEY, transport=httpx.MockTransport(handler))
    proposal, _ = client.generate(model="vendor/model", system="safe", context={})
    assert [q.id for q in proposal.questions] == ["Q-01"]
    assert proposal.modules == []
    assert proposal.domain_assessments == []
    schema = json.loads(seen[0].content)["response_format"]["json_schema"]["schema"]
    branches = schema["properties"]["result"]["anyOf"]
    options = [schema["$defs"][branch["$ref"].split("/")[-1]] for branch in branches]
    questions = next(
        option for option in options if option["properties"]["kind"].get("const") == "questions"
    )
    assert "modules" not in questions["properties"]
    assert "profiles" not in questions["properties"]
    assert questions["additionalProperties"] is False


def test_clarification_does_not_silently_accept_a_speculative_draft():
    result = {
        "kind": "questions",
        "architecture": "Decisão pendente de contexto do negócio",
        "rationale": "Precisamos conhecer os processos antes de gerar regras ou estruturas.",
        "questions": [{"id": "Q-01", "question": "Quais são os processos e regras deste produto?"}],
        "modules": [{"name": "speculative"}],
    }
    client = OpenRouter(
        api_key=TEST_KEY,
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": json.dumps({"result": result})},
                        }
                    ]
                },
            )
        ),
    )
    with pytest.raises(WorkflowError, match="schema"):
        client.generate(model="vendor/model", system="safe", context={})


def test_wire_contract_encodes_rule_categories_and_citation_options(draft):
    seen = []
    client_for(draft, seen).generate(
        model="vendor/model",
        system="safe",
        context={
            "domain_sources": {"BRIEF": "API de pedidos com invariantes. Pedidos possuem estados."}
        },
    )
    schema = json.loads(seen[0].content)["response_format"]["json_schema"]["schema"]
    sections = schema["$defs"]["RuleSections"]
    assert {"design", "security", "testing"}.issubset(sections["required"])
    evidence = schema["$defs"]["ConclusiveAssessment"]["properties"]["evidence"]
    assert evidence["minItems"] == 1
    quote = schema["$defs"]["DomainEvidence"]["properties"]["quote"]
    assert quote["enum"] == ["API de pedidos com invariantes.", "Pedidos possuem estados."]
    refs = schema["$defs"]["DomainPattern"]["properties"]["evidence_ids"]["items"]
    assert refs["pattern"] == r"^E-[0-9]{2,}$"


def test_continuation_contract_does_not_offer_the_short_interview_branch(draft):
    seen = []
    proposal, _ = client_for(draft, seen).generate(
        model="vendor/model",
        system="safe",
        context={"answers": ["Q-01=CRUD simples sem aprovações adicionais"]},
    )
    assert not proposal.questions
    schema = json.loads(seen[0].content)["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["result"] == {"$ref": "#/$defs/CompleteResponse"}
