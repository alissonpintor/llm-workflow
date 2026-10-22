from __future__ import annotations

import re
from dataclasses import dataclass

from .config import WorkflowError

NAME = r"[a-zA-Z][a-zA-Z0-9_-]*"
MODULE_RE = re.compile(rf"^(?P<name>{NAME}):(?P<kind>{NAME})=(?P<profiles>{NAME}(?:\+{NAME})*)$")
SERVICE_RE = re.compile(rf"^(?P<name>{NAME})=(?P<profile>{NAME})$")
USES_RE = re.compile(rf"^(?P<module>{NAME})=(?P<services>{NAME}(?:,{NAME})*)$")
SETTING_RE = re.compile(rf"^(?P<scope>{NAME})\.(?P<key>{NAME})=(?P<value>.+)$")


@dataclass(frozen=True)
class ModuleSpec:
    name: str
    kind: str
    profiles: list[str]


def parse_module(value: str) -> ModuleSpec:
    match = MODULE_RE.fullmatch(value)
    if not match:
        raise WorkflowError(
            f"Módulo inválido '{value}'. Use nome:tipo=perfil+perfil, "
            "ex.: api:backend=python+fastapi."
        )
    return ModuleSpec(match.group("name"), match.group("kind"), match.group("profiles").split("+"))


def parse_service(value: str) -> tuple[str, str]:
    match = SERVICE_RE.fullmatch(value)
    if not match:
        raise WorkflowError(f"Serviço inválido '{value}'. Use nome=perfil, ex.: database=postgres.")
    return match.group("name"), match.group("profile")


def parse_uses(value: str) -> tuple[str, list[str]]:
    match = USES_RE.fullmatch(value)
    if not match:
        raise WorkflowError(
            f"Uso inválido '{value}'. Use modulo=servico,servico, ex.: api=database,cache."
        )
    return match.group("module"), match.group("services").split(",")


def parse_setting(value: str) -> tuple[str, str, str]:
    match = SETTING_RE.fullmatch(value)
    if not match:
        raise WorkflowError(
            f"Configuração inválida '{value}'. Use escopo.chave=valor, "
            "ex.: api.package_manager=pnpm."
        )
    return match.group("scope"), match.group("key"), match.group("value")
