from __future__ import annotations

from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

from .config import WorkflowError, read_yaml, safe_path


@dataclass(frozen=True)
class Profile:
    id: str
    name: str
    category: str
    requires: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    kinds: tuple[str, ...] = ()
    gates: tuple[dict[str, Any], ...] = ()
    rule: str = ""
    techspec_guidance: tuple[str, ...] = ()
    edge_cases: tuple[str, ...] = ()
    defaults: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Plugin:
    id: str
    name: str
    description: str
    paths: tuple[str, ...]
    run_at: tuple[str, ...]
    rule: str
    files: tuple[dict[str, str], ...] = ()


def _assets():
    return files("llm_feature_workflow").joinpath("assets")


def profile_from_data(data: dict[str, Any]) -> Profile:
    import re

    if not isinstance(data.get("id"), str) or not re.fullmatch(r"[a-z][a-z0-9-]*", data["id"]):
        raise WorkflowError("Perfil local: ID inválido.")
    if data.get("category") not in {
        "language",
        "framework",
        "runtime",
        "platform",
        "ui",
        "service",
    }:
        raise WorkflowError("Perfil local: category inválida.")
    for key in ("requires", "conflicts", "kinds", "techspec_guidance", "edge_cases"):
        value = data.get(key, [])
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise WorkflowError(f"Perfil local: {key} deve ser lista de textos.")
    if not isinstance(data.get("rule", ""), str):
        raise WorkflowError("Perfil local: rule deve ser texto.")
    if not isinstance(data.get("name", data["id"]), str):
        raise WorkflowError("Perfil local: name deve ser texto.")
    defaults = data.get("defaults", {})
    if not isinstance(defaults, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in defaults.items()
    ):
        raise WorkflowError("Perfil local: defaults deve conter textos.")
    gates = data.get("gates", [])
    if not isinstance(gates, list) or not all(
        isinstance(g, dict)
        and all(isinstance(g.get(k), str) for k in ("id", "command"))
        and isinstance(g.get("working_directory", ""), str)
        for g in gates
    ):
        raise WorkflowError("Perfil local: gates inválidos.")
    return Profile(
        id=data["id"],
        name=data.get("name", data["id"]),
        category=data["category"],
        requires=tuple(data.get("requires", [])),
        conflicts=tuple(data.get("conflicts", [])),
        kinds=tuple(data.get("kinds", [])),
        gates=tuple(gates),
        rule=data.get("rule", ""),
        techspec_guidance=tuple(data.get("techspec_guidance", [])),
        edge_cases=tuple(data.get("edge_cases", [])),
        defaults=defaults,
    )


def load_profiles(root: Path | None = None) -> dict[str, Profile]:
    result: dict[str, Profile] = {}
    directory = _assets().joinpath("profiles")
    for entry in directory.iterdir():
        manifest = entry.joinpath("profile.yaml")
        if not manifest.is_file():
            continue
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        profile = profile_from_data(data)
        result[profile.id] = profile
    if root is not None:
        local = safe_path(root, ".workflow/profiles")
        if local.is_dir():
            for entry in sorted(local.iterdir()):
                relative = f".workflow/profiles/{entry.name}/profile.yaml"
                manifest = safe_path(root, relative)
                if not manifest.is_file():
                    continue
                if manifest.stat().st_size > 256_000:
                    raise WorkflowError("Perfil local excede o limite de tamanho.")
                profile = profile_from_data(read_yaml(manifest))
                if profile.id != entry.name or profile.id in result:
                    raise WorkflowError(
                        "Perfil local deve ter ID igual à pasta e não substituir perfil existente."
                    )
                result[profile.id] = profile
    return result


def load_plugins() -> dict[str, Plugin]:
    result: dict[str, Plugin] = {}
    directory = _assets().joinpath("plugins")
    for entry in directory.iterdir():
        manifest = entry.joinpath("plugin.yaml")
        if not manifest.is_file():
            continue
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        plugin = Plugin(
            id=data["id"],
            name=data.get("name", data["id"]),
            description=data.get("description", ""),
            paths=tuple(data.get("paths", [])),
            run_at=tuple(data.get("run_at", [])),
            rule=data.get("rule", ""),
            files=tuple(data.get("files", [])),
        )
        result[plugin.id] = plugin
    return result


def resolve_profiles(requested: list[str], registry: dict[str, Profile]) -> list[str]:
    resolved: list[str] = []
    visiting: set[str] = set()

    def visit(profile_id: str) -> None:
        if profile_id in resolved:
            return
        if profile_id in visiting:
            raise WorkflowError(f"Ciclo de dependência entre perfis envolvendo '{profile_id}'.")
        profile = registry.get(profile_id)
        if not profile:
            choices = ", ".join(sorted(registry))
            raise WorkflowError(
                f"Perfil desconhecido '{profile_id}'. Disponíveis: {choices}. "
                "Crie um perfil local em .workflow/profiles/<id>/profile.yaml "
                "ou use configure --ai para propor um."
            )
        visiting.add(profile_id)
        for requirement in profile.requires:
            visit(requirement)
        visiting.remove(profile_id)
        resolved.append(profile_id)

    for item in requested:
        visit(item)

    selected = set(resolved)
    for profile_id in resolved:
        conflicts = selected.intersection(registry[profile_id].conflicts)
        if conflicts:
            raise WorkflowError(
                f"Perfil '{profile_id}' conflita com: {', '.join(sorted(conflicts))}. "
                "Use módulos separados."
            )
    return resolved


def validate_kind(kind: str, profile_ids: list[str], registry: dict[str, Profile]) -> None:
    for profile_id in profile_ids:
        allowed = registry[profile_id].kinds
        if allowed and kind not in allowed:
            raise WorkflowError(
                f"Perfil '{profile_id}' não se aplica ao módulo do tipo '{kind}'. "
                f"Tipos aceitos: {', '.join(allowed)}"
            )
