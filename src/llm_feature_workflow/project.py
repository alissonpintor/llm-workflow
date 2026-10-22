"""Normalize and validate project configuration before generating any files."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

from .config import WorkflowError, safe_path
from .profiles import load_plugins, load_profiles, resolve_profiles, validate_kind

TARGETS = {"agents", "grok", "zcode", "opencode"}
KINDS = {"backend", "frontend", "worker", "mobile", "library", "cli"}


def _strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise WorkflowError(f"{label} deve ser uma lista de textos.")
    return value


def normalize_config(root: Path, raw: dict[str, Any]) -> dict[str, Any]:
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
    registry = load_profiles()
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
    return config
