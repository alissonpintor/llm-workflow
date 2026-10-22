from __future__ import annotations

from dataclasses import dataclass, field
from importlib.resources import files
from typing import Any

import yaml

from .config import WorkflowError


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


def load_profiles() -> dict[str, Profile]:
    result: dict[str, Profile] = {}
    directory = _assets().joinpath("profiles")
    for entry in directory.iterdir():
        manifest = entry.joinpath("profile.yaml")
        if not manifest.is_file():
            continue
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        profile = Profile(
            id=data["id"],
            name=data.get("name", data["id"]),
            category=data["category"],
            requires=tuple(data.get("requires", [])),
            conflicts=tuple(data.get("conflicts", [])),
            kinds=tuple(data.get("kinds", [])),
            gates=tuple(data.get("gates", [])),
            rule=data.get("rule", ""),
            techspec_guidance=tuple(data.get("techspec_guidance", [])),
            edge_cases=tuple(data.get("edge_cases", [])),
            defaults=data.get("defaults", {}),
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
            raise WorkflowError(f"Perfil desconhecido '{profile_id}'. Disponíveis: {choices}")
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
