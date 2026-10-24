"""Normalize and validate project configuration before generating any files."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

from .config import WorkflowError, safe_path
from .profiles import Profile, load_plugins, load_profiles, resolve_profiles, validate_kind

TARGETS = {"agents", "grok", "zcode", "opencode"}
KINDS = {"backend", "frontend", "worker", "mobile", "library", "cli"}


def _strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise WorkflowError(f"{label} deve ser uma lista de textos.")
    return value


def normalize_config(
    root: Path, raw: dict[str, Any], registry: dict[str, Profile] | None = None
) -> dict[str, Any]:
    config = copy.deepcopy(raw)
    if config.get("schema_version") != 1:
        raise WorkflowError("schema_version não suportada; esperado 1.")
    for section in ("project", "agents", "modules", "services"):
        if not isinstance(config.get(section), dict):
            raise WorkflowError(f"{section} deve ser um objeto.")
    targets = _strings(config["agents"].get("targets"), "agents.targets")
    if set(targets) - TARGETS:
        raise WorkflowError("Adaptador desconhecido em agents.targets.")
    plugin_ids = _strings(config.get("plugins", []), "plugins")
    if set(plugin_ids) - set(load_plugins()):
        raise WorkflowError("Plugin desconhecido na configuração.")
    if "ai" in config:
        from .ai_models import valid_model_id

        ai = config["ai"]
        if not isinstance(ai, dict) or set(ai) != {"provider", "model", "max_output_tokens"}:
            raise WorkflowError("ai aceita só provider, model e max_output_tokens; nunca chaves.")
        if ai["provider"] != "openrouter":
            raise WorkflowError("O provedor de LLM suportado é openrouter.")
        try:
            valid_model_id(ai["model"])
        except (ValueError, TypeError):
            raise WorkflowError("ai.model inválido.") from None
        if type(ai["max_output_tokens"]) is not int or not 512 <= ai["max_output_tokens"] <= 16000:
            raise WorkflowError("ai.max_output_tokens deve estar entre 512 e 16000.")
    registry = load_profiles(root) if registry is None else registry
    for section in ("modules", "services"):
        for name, item in config[section].items():
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", name):
                raise WorkflowError(f"Nome inválido em {section}.")
            if not isinstance(item, dict):
                raise WorkflowError(f"{section}.{name} deve ser um objeto.")
            requested = _strings(item.get("requested_profiles"), f"{name}.requested_profiles")
            if not requested:
                raise WorkflowError(f"{name}: informe pelo menos um perfil.")
            resolved = resolve_profiles(requested, registry)
            item["resolved_profiles"] = resolved
            settings = item.setdefault("settings", {})
            if not isinstance(settings, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in settings.items()
            ):
                raise WorkflowError(f"{name}.settings deve conter textos.")
            if section == "modules":
                guidance = item.get("guidance", "")
                if not isinstance(guidance, str) or len(guidance) > 150_000:
                    raise WorkflowError(f"{name}.guidance deve ser texto de até 150000 caracteres.")
                proposed_gates = item.get("proposed_gates", [])
                if not isinstance(proposed_gates, list) or not all(
                    isinstance(g, dict)
                    and all(isinstance(g.get(k), str) for k in ("id", "command", "purpose"))
                    for g in proposed_gates
                ):
                    raise WorkflowError(f"{name}.proposed_gates inválido.")
                if item.get("kind") not in KINDS:
                    raise WorkflowError(f"Tipo de módulo inválido: {name}.")
                if any(registry[p].category == "service" for p in resolved):
                    raise WorkflowError(f"{name}: configure serviços com --service, não --module.")
                validate_kind(item["kind"], resolved, registry)
                module_path = item.setdefault("path", name)
                if not isinstance(module_path, str):
                    raise WorkflowError(f"{name}.path deve ser texto.")
                safe_path(root, module_path)
                uses = _strings(item.setdefault("uses", []), f"{name}.uses")
                if set(uses) - set(config["services"]):
                    raise WorkflowError(f"{name}: referência a serviço inexistente.")
            elif any(registry[p].category != "service" for p in resolved):
                raise WorkflowError(f"{name}: perfil não é serviço.")
    config["project"]["status"] = "configured" if config["modules"] else "stack-undecided"
    if "domain_assessments" in config:
        from pydantic import ValidationError

        from .ai_models import DomainAssessment, validate_assessment_links

        try:
            if not isinstance(config["domain_assessments"], list):
                raise ValueError("expected list")
            assessments = [DomainAssessment.model_validate(a) for a in config["domain_assessments"]]
            validate_assessment_links(assessments, set(config["modules"]), set())
        except (ValueError, ValidationError):
            raise WorkflowError("domain_assessments inválido ou com perguntas pendentes.") from None
    return config
