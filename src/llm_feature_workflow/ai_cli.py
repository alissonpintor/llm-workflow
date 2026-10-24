from __future__ import annotations

import argparse
import getpass
import os
import sys
import warnings

from .ai_models import valid_model_id
from .ai_workflow import (
    apply_proposal,
    generate_proposal,
    proposal_report,
    read_record,
    safe_display,
    validate_brief,
)
from .config import WorkflowError, load_config
from .openrouter import OpenRouter
from .project import normalize_config
from .renderer import materialize


def setup(args: argparse.Namespace) -> int:
    root = args.path.resolve()
    model = args.model
    if not model:
        if not sys.stdin.isatty():
            raise WorkflowError("Informe --model; liste as opções com llm-workflow llm models.")
        model = input("ID do modelo no OpenRouter (fornecedor/modelo): ").strip()
    try:
        valid_model_id(model)
    except ValueError as error:
        raise WorkflowError(str(error)) from None
    if not 512 <= args.max_tokens <= 16000:
        raise WorkflowError("--max-tokens deve estar entre 512 e 16000.")
    config = load_config(root)
    config["ai"] = {"provider": "openrouter", "model": model, "max_output_tokens": args.max_tokens}
    materialize(root, config)
    print("OpenRouter configurado sem chave em arquivo e sem chamada de geração.")
    if os.environ.get("OPENROUTER_API_KEY", "").strip():
        print("OPENROUTER_API_KEY detectada neste processo; validade não verificada na API.")
    else:
        print(
            "OPENROUTER_API_KEY não está visível neste processo; defina-a antes de configure --ai."
        )
    print("Arquivos .env não são carregados automaticamente.")
    return 0


def models(args: argparse.Namespace) -> int:
    rows = OpenRouter().models(args.filter)
    for row in rows:
        print(safe_display(f"{row['id']} — {row['name']}"))
    print(f"{len(rows)} modelo(s) com structured_outputs no catálogo; valide acesso na sua conta.")
    return 0


def configure(args: argparse.Namespace) -> int:
    root = args.path.resolve()
    if args.config:
        raise WorkflowError("Não combine --ai com --config; importe a configuração primeiro.")
    if args.portable or args.agents is not None:
        raise WorkflowError("Selecione adaptadores em configure sem --ai antes de gerar.")
    config = normalize_config(root, load_config(root))
    settings = config.get("ai", {})
    model = args.model or settings.get("model")
    if not model:
        raise WorkflowError("Escolha --model ou execute llm-workflow llm setup primeiro.")
    try:
        valid_model_id(model)
    except ValueError as error:
        raise WorkflowError(str(error)) from None
    brief = args.brief
    if not brief and args.answer:
        brief = read_record(root).brief
    if not brief:
        if not sys.stdin.isatty():
            raise WorkflowError("Informe --brief descrevendo objetivo, arquitetura e restrições.")
        brief = input("Descreva o projeto, stack, arquitetura desejada e restrições: ").strip()
    validate_brief(brief)
    max_tokens = (
        args.max_tokens if args.max_tokens is not None else settings.get("max_output_tokens", 8000)
    )
    if not 512 <= max_tokens <= 16000:
        raise WorkflowError("--max-tokens deve estar entre 512 e 16000.")
    requests = (
        [f"module {value}" for value in args.module]
        + [f"service {value}" for value in args.service]
        + [f"uses {value}" for value in args.uses]
        + [f"setting {value}" for value in args.setting]
    )
    if args.plugin:
        raise WorkflowError("Ative plugins em configure sem --ai; a LLM não instala código.")
    print("Destino: https://openrouter.ai/api/v1/chat/completions")
    print(f"Modelo: {model}; máximo de saída: {max_tokens} tokens; 1 geração nesta execução.")
    print("Envio: brief, respostas, solicitações e metadados de módulos/serviços.")
    print("Não enviamos código, settings existentes, .env, docs privados ou credencial no prompt.")
    print("A chamada pode ser cobrada. Revise as recomendações e os gates propostos.")
    if not args.allow_paid:
        if args.non_interactive or not sys.stdin.isatty():
            raise WorkflowError("Confirme envio/custo com --allow-paid ou use um terminal.")
        if input("Autorizar esse envio e possível cobrança? [s/N]: ").strip().lower() not in {
            "s",
            "sim",
            "y",
            "yes",
        }:
            print("Envio cancelado; nada aplicado.")
            return 0
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key and sys.stdin.isatty() and not args.non_interactive:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", getpass.GetPassWarning)
                key = getpass.getpass("Chave OpenRouter (uso nesta chamada; não será salva): ")
        except getpass.GetPassWarning:
            raise WorkflowError(
                "Entrada oculta indisponível. Defina OPENROUTER_API_KEY no ambiente."
            ) from None
    if not key:
        raise WorkflowError("Defina OPENROUTER_API_KEY; não passe a chave como argumento da CLI.")
    record = generate_proposal(
        root,
        model=model,
        brief=brief,
        requests=requests,
        answers=args.answer,
        max_tokens=max_tokens,
        client=OpenRouter(api_key=key),
    )
    print("Proposta salva em .workflow/ai/proposal.json; workflow ainda não alterado.")
    for question in record.proposal.questions:
        print(safe_display(f"{question.id}: {question.question}"))
    print("Revise: llm-workflow llm preview .")
    print("Aplique separadamente: llm-workflow llm apply . --approve")
    return 0


def preview(args: argparse.Namespace) -> int:
    root = args.path.resolve()
    print(proposal_report(root, read_record(root)))
    return 0


def apply(args: argparse.Namespace) -> int:
    if not args.approve:
        raise WorkflowError("Revise llm preview antes; --approve é obrigatório para aplicar.")
    apply_proposal(args.path.resolve())
    print("Proposta aplicada. Nenhum comando sugerido ou código da aplicação foi executado.")
    return 0


def add_llm_parser(subparsers) -> None:
    from pathlib import Path

    llm = subparsers.add_parser("llm", help="OpenRouter: modelos, setup, preview e aplicação")
    commands = llm.add_subparsers(dest="llm_command", required=True)
    catalog = commands.add_parser("models", help="Consulta catálogo público, sem geração paga")
    catalog.add_argument("--filter", default="")
    catalog.set_defaults(func=models)
    init = commands.add_parser("setup", help="Salva modelo e limites; nunca salva chave")
    init.add_argument("path", type=Path, nargs="?", default=Path("."))
    init.add_argument("--model")
    init.add_argument("--max-tokens", type=int, default=8000)
    init.set_defaults(func=setup)
    for name, handler in (("preview", preview), ("apply", apply)):
        parser = commands.add_parser(name)
        parser.add_argument("path", type=Path, nargs="?", default=Path("."))
        if name == "apply":
            parser.add_argument("--approve", action="store_true")
        parser.set_defaults(func=handler)
