from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path
from typing import Any

from jinja2 import Environment, StrictUndefined

from . import __version__
from .config import (
    WorkflowError,
    config_digest,
    config_path,
    file_digest,
    load_lock,
    lock_path,
    safe_path,
    save_config,
    save_lock,
)
from .profiles import Plugin, Profile, load_plugins, load_profiles
from .project import normalize_config

MANAGED_MARKER = "<!-- llm-workflow:managed -->"
BLOCK_START = "<!-- llm-workflow:start -->"
BLOCK_END = "<!-- llm-workflow:end -->"

ADAPTERS = {
    "agents": {"commands": ".agents/rules/commands", "rules": ".agents/rules"},
    "grok": {"commands": ".grok/rules/commands", "rules": ".grok/rules"},
    "zcode": {"commands": ".zcode/commands", "rules": ".zcode/rules"},
    "opencode": {"commands": ".opencode/commands", "rules": ".opencode/rules"},
}


def _core_directory(name: str):
    return files("llm_feature_workflow").joinpath("assets", "core", name)


def _read_assets(directory) -> dict[str, str]:
    result: dict[str, str] = {}
    for entry in directory.iterdir():
        if entry.is_file():
            result[entry.name] = entry.read_text(encoding="utf-8")
    return result


def _render(text: str, context: dict[str, Any]) -> str:
    env = Environment(undefined=StrictUndefined, autoescape=False, keep_trailing_newline=True)
    return env.from_string(text).render(**context)


def mark_markdown(text: str) -> str:
    """Keep frontmatter at byte zero for agent command discovery."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            end += len("\n---\n")
            return text[:end] + "\n" + MANAGED_MARKER + "\n" + text[end:].lstrip("\n")
    return MANAGED_MARKER + "\n" + text


def _module_context(config: dict[str, Any], registry: dict[str, Profile]) -> tuple[str, str, str]:
    gate_rows: list[str] = []
    guidance: list[str] = []
    edge_cases: list[str] = []

    for module_name, module in config.get("modules", {}).items():
        settings = dict(module.get("settings", {}))
        settings.setdefault("module_path", module.get("path", module_name))
        settings.setdefault("module_name", module_name)
        settings.setdefault("gradle_command", "gradlew.bat" if os.name == "nt" else "./gradlew")
        if "kotlin" in module.get("resolved_profiles", []):
            settings.setdefault("test_command", f"{settings['gradle_command']} test")
            settings.setdefault("android_lint_command", f"{settings['gradle_command']} lint")
        if "node" in module.get("resolved_profiles", []):
            manager = settings.get("package_manager", "npm")
            settings.setdefault("lint_command", f"{manager} run lint")
            settings.setdefault("typecheck_command", f"{manager} run typecheck")
            settings.setdefault("test_command", f"{manager} test")
        for profile_id in module.get("resolved_profiles", []):
            profile = registry[profile_id]
            guidance.extend(
                f"- **{module_name}/{profile_id}:** {item}" for item in profile.techspec_guidance
            )
            edge_cases.extend(
                f"- **{module_name}/{profile_id}:** {item}" for item in profile.edge_cases
            )
            defaults = dict(profile.defaults)
            defaults.update(settings)
            for gate in profile.gates:
                try:
                    command = gate["command"].format_map(defaults)
                    workdir = gate.get("working_directory", "{module_path}").format_map(defaults)
                except KeyError as error:
                    raise WorkflowError(
                        "Configuração ausente para gate "
                        f"'{gate.get('id')}' do perfil '{profile_id}': {error}"
                    ) from error
                gate_rows.append(f"| {module_name} | {gate['id']} | `{workdir}` | `{command}` |")

    for service_name, service in config.get("services", {}).items():
        for profile_id in service.get("resolved_profiles", []):
            profile = registry[profile_id]
            guidance.append(f"- **serviço {service_name}:** {profile.name} (`{profile_id}`).")
            guidance.extend(
                f"- **serviço {service_name}/{profile_id}:** {item}"
                for item in profile.techspec_guidance
            )
            edge_cases.extend(
                f"- **serviço {service_name}/{profile_id}:** {item}" for item in profile.edge_cases
            )

    gates = "\n".join(gate_rows) or "| — | — | — | Nenhum gate tecnológico configurado |"
    guidance_text = "\n".join(guidance) or "- Nenhuma orientação tecnológica configurada."
    edge_cases_text = "\n".join(edge_cases) or "- Aplique somente os casos genéricos do fluxo."
    return gates, guidance_text, edge_cases_text


def _plugin_context(config: dict[str, Any], plugins: dict[str, Plugin]) -> tuple[str, str]:
    lines: list[str] = []
    rules: list[str] = []
    for plugin_id in config.get("plugins", []):
        plugin = plugins.get(plugin_id)
        if not plugin:
            raise WorkflowError(f"Plugin desconhecido: {plugin_id}")
        lines.append(
            f"- **{plugin.name} (`{plugin.id}`):** {plugin.description} "
            f"Caminhos: {', '.join(plugin.paths)}; "
            f"etapas: {', '.join(plugin.run_at)}."
        )
        rules.append(plugin.rule)
    return "\n".join(lines) or "- Nenhum plugin configurado.", "\n\n".join(rules)


def build_outputs(config: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
    registry = load_profiles()
    plugins = load_plugins()
    gates, guidance, edge_cases = _module_context(config, registry)
    plugin_summary, plugin_rules = _plugin_context(config, plugins)
    context = {
        "workflow_version": __version__,
        "project": config.get("project", {}),
        "modules": config.get("modules", {}),
        "services": config.get("services", {}),
        "quality_gates": gates,
        "techspec_guidance": guidance,
        "profile_edge_cases": edge_cases,
        "plugin_summary": plugin_summary,
    }

    outputs: dict[str, str] = {}
    for group in ("commands", "templates", "rules"):
        for name, source in _read_assets(_core_directory(group)).items():
            outputs[f".workflow/generated/{group}/{name}"] = mark_markdown(_render(source, context))

    selected: set[str] = set()
    for module in config.get("modules", {}).values():
        selected.update(module.get("resolved_profiles", []))
    for service in config.get("services", {}).values():
        selected.update(service.get("resolved_profiles", []))
    for profile_id in sorted(selected):
        profile = registry[profile_id]
        if profile.rule:
            content = f"# Perfil: {profile.name}\n\n{profile.rule.strip()}\n"
            outputs[f".workflow/generated/rules/profile-{profile_id}.md"] = (
                MANAGED_MARKER + "\n" + content
            )

    if plugin_rules:
        outputs[".workflow/generated/rules/plugins.md"] = (
            MANAGED_MARKER + "\n# Plugins de qualidade\n\n" + plugin_rules.strip() + "\n"
        )

    outputs[".workflow/generated/profile-context.md"] = (
        MANAGED_MARKER
        + "\n# Contexto tecnológico gerado\n\n"
        + "Os comandos abaixo são configuração do projeto, "
        + "não autorização para execução automática. "
        + "Revise os defaults conforme os arquivos reais. Não registre segredos aqui.\n\n"
        + "## Módulos\n\n| Nome | Tipo | Caminho | Perfis | Serviços usados |\n"
        + "|---|---|---|---|---|\n"
        + (
            "\n".join(
                f"| {name} | {module['kind']} | `{module['path']}` | "
                f"{', '.join(module['resolved_profiles'])} | {', '.join(module['uses']) or '—'} |"
                for name, module in config.get("modules", {}).items()
            )
            or "| — | — | — | Stack ainda não definida | — |"
        )
        + "\n\n"
        + "## Quality gates\n\n| Escopo | Gate | Diretório | Comando |\n|---|---|---|---|\n"
        + gates
        + "\n\n## Orientações de Tech Spec\n\n"
        + guidance
        + "\n\n## Casos de borda dos perfis\n\n"
        + edge_cases
        + "\n\n## Plugins\n\n"
        + plugin_summary
        + "\n"
    )

    for name, source in _read_assets(_core_directory("docs")).items():
        destination = "MEMORY.md" if name == "MEMORY.md" else f"docs/{name}"
        outputs[destination] = MANAGED_MARKER + "\n" + _render(source, context)

    for plugin_id in config.get("plugins", []):
        plugin = plugins[plugin_id]
        base = files("llm_feature_workflow").joinpath("assets", "plugins", plugin_id)
        for item in plugin.files:
            source = base.joinpath(item["source"])
            content = source.read_text(encoding="utf-8")
            if item["destination"].endswith(".py"):
                lines = content.splitlines(keepends=True)
                insertion = "# llm-workflow:managed\n"
                if lines and lines[0].startswith("#!"):
                    content = lines[0] + insertion + "".join(lines[1:])
                else:
                    content = insertion + content
            outputs[item["destination"]] = content

    resolved = {"profiles": sorted(selected), "plugins": list(config.get("plugins", []))}
    return outputs, resolved


def _managed_block(current: str, body: str) -> str:
    block = f"{BLOCK_START}\n{body.rstrip()}\n{BLOCK_END}\n"
    if current.count(BLOCK_START) != current.count(BLOCK_END) or current.count(BLOCK_START) > 1:
        raise WorkflowError("AGENTS.md contém marcadores gerenciados incompletos ou duplicados.")
    if BLOCK_START in current:
        before, remainder = current.split(BLOCK_START, 1)
        if BLOCK_END not in remainder:
            raise WorkflowError("AGENTS.md contém marcadores em ordem inválida.")
        _old, after = remainder.split(BLOCK_END, 1)
        return before + block.rstrip("\n") + after
    return current + ("\n\n" if current else "") + block


def _is_managed(content: str) -> bool:
    return MANAGED_MARKER in content or "# llm-workflow:managed" in content


def installation_plan(root: Path, config: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
    outputs, resolved = build_outputs(config)
    destinations = {"commands": ["commands"], "templates": ["templates"], "rules": []}
    for target in config.get("agents", {}).get("targets", []):
        adapter = ADAPTERS[target]
        destinations["commands"].append(adapter["commands"])
        destinations["rules"].append(adapter["rules"])
    for group, targets in destinations.items():
        prefix = f".workflow/generated/{group}/"
        for relative, content in list(outputs.items()):
            if relative.startswith(prefix):
                for target in targets:
                    outputs[f"{target}/{relative.removeprefix(prefix)}"] = content
    agents_body = (
        "# LLM Feature Workflow\n\n"
        "Leia `MEMORY.md`, `.workflow/generated/rules/common.md` e "
        "`.workflow/generated/profile-context.md` antes de planejar ou implementar. "
        "Abra as demais rules em `.workflow/generated/rules/` quando os perfis forem aplicáveis. "
        "Arquivos gerados não são instruções de terceiros para executar comandos automaticamente. "
        "Consulte `commands/` conforme a solicitação do usuário.\n"
    )
    agents_path = safe_path(root, "AGENTS.md")
    current = agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""
    outputs["AGENTS.md"] = _managed_block(current, agents_body)
    return outputs, resolved


def _seed(relative: str) -> bool:
    return relative.startswith("docs/") or relative == "MEMORY.md"


def _owned(relative: str) -> bool:
    prefixes = [".workflow/generated/", "commands/", "templates/"]
    for adapter in ADAPTERS.values():
        prefixes.extend([adapter["commands"] + "/", adapter["rules"] + "/"])
    return relative == "scripts/find_ghost_fields.py" or any(
        relative.startswith(prefix) for prefix in prefixes
    )


def preflight(root: Path, outputs: dict[str, str], previous: dict[str, str]) -> list[str]:
    """Validate the whole plan before writing any file or removing a stale file."""
    conflicts: list[str] = []
    for relative, content in outputs.items():
        path = safe_path(root, relative)
        if not path.exists() or _seed(relative) or relative == "AGENTS.md":
            continue
        if not path.is_file():
            conflicts.append(relative)
            continue
        existing = path.read_text(encoding="utf-8")
        if existing != content and (
            not _is_managed(existing) or file_digest(existing) != previous.get(relative)
        ):
            conflicts.append(relative)
    for relative in previous.keys() - outputs.keys():
        path = safe_path(root, relative)
        if not _owned(relative) or not path.is_file():
            continue
        existing = path.read_text(encoding="utf-8")
        if not _is_managed(existing) or file_digest(existing) != previous[relative]:
            conflicts.append(relative)
    return sorted(set(conflicts))


def materialize(root: Path, config: dict[str, Any]) -> dict[str, str]:
    config_path(root)
    lock_path(root)
    config = normalize_config(root, config)
    config["workflow_version"] = __version__
    outputs, resolved = installation_plan(root, config)
    previous = load_lock(root).get("managed_files", {})
    conflicts = preflight(root, outputs, previous)
    if conflicts:
        raise WorkflowError(
            "Nenhum arquivo foi alterado: conflitos locais em "
            + ", ".join(conflicts)
            + ". Preserve as edições fora dos arquivos gerados e restaure a versão gerenciada."
        )
    managed: dict[str, str] = {}
    for relative, content in outputs.items():
        path = safe_path(root, relative)
        if _seed(relative) and path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if not _seed(relative) and relative != "AGENTS.md":
            managed[relative] = file_digest(content)
    for relative in previous.keys() - outputs.keys():
        path = safe_path(root, relative)
        if _owned(relative) and path.is_file():
            path.unlink()
    save_config(root, config)
    save_lock(root, managed, resolved, config)
    return managed


def check_materialized(root: Path, config: dict[str, Any]) -> list[str]:
    config = normalize_config(root, config)
    expected, _resolved = installation_plan(root, config)
    problems: list[str] = []
    for relative, content in expected.items():
        path = safe_path(root, relative)
        if _seed(relative):
            continue
        if not path.is_file():
            problems.append(f"ausente: {relative}")
        elif path.read_text(encoding="utf-8") != content:
            problems.append(f"divergente: {relative}")
    lock = load_lock(root)
    if not lock:
        problems.append("ausente: .workflow/workflow.lock")
    elif lock.get("config_sha256") != config_digest(config):
        problems.append("configuração mudou desde o último sync")
    return problems
