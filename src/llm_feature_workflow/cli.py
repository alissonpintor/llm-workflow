from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import __version__
from .config import WorkflowError, default_config, load_config, read_yaml, safe_path
from .profiles import load_plugins, load_profiles, resolve_profiles, validate_kind
from .project import normalize_config
from .renderer import ADAPTERS, check_materialized, installation_plan, materialize
from .specs import parse_module, parse_service, parse_setting, parse_uses
from .validator import validate_feature


def root_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def cmd_init(args: argparse.Namespace) -> int:
    root = root_path(args.path)
    root.mkdir(parents=True, exist_ok=True)
    config_file = root / ".workflow" / "workflow.yaml"
    if config_file.exists() and not args.force:
        raise WorkflowError(f"Workflow já inicializado: {config_file}")
    unknown = sorted(set(args.agents) - set(ADAPTERS))
    if unknown:
        raise WorkflowError(f"Adaptadores desconhecidos: {', '.join(unknown)}")
    config = default_config(root, args.agents)
    materialize(root, config)
    print(f"Workflow {__version__} inicializado em {root}")
    print("Próximo passo: execute 'llm-workflow configure .'.")
    return 0


def _interactive_modules() -> tuple[list[str], list[str], list[str]]:
    modules: list[str] = []
    services: list[str] = []
    uses: list[str] = []
    print("Configuração interativa. Pressione Enter sem nome para encerrar cada grupo.")
    while True:
        name = input("Nome do módulo (ex.: api): ").strip()
        if not name:
            break
        kind = input("Tipo (backend/frontend/worker/mobile/library/cli): ").strip() or "backend"
        profiles = input("Perfis separados por + (ex.: python+fastapi): ").strip()
        modules.append(f"{name}:{kind}={profiles}")
    while True:
        name = input("Nome do serviço compartilhado (Enter para terminar): ").strip()
        if not name:
            break
        profile = input("Perfil do serviço (ex.: postgres ou redis): ").strip()
        services.append(f"{name}={profile}")
    for module in modules:
        module_name = module.split(":", 1)[0]
        value = input(f"Serviços usados por {module_name}, separados por vírgula: ").strip()
        if value:
            uses.append(f"{module_name}={value}")
    return modules, services, uses


def cmd_configure(args: argparse.Namespace) -> int:
    root = root_path(args.path)
    if args.ai:
        from .ai_cli import configure

        args.path = root
        return configure(args)
    raw_config = read_yaml(root_path(args.config)) if args.config else load_config(root)
    config = normalize_config(root, raw_config)
    if args.portable:
        config["agents"]["targets"] = []
    elif args.agents is not None:
        config["agents"]["targets"] = args.agents
    registry = load_profiles(root)
    plugin_registry = load_plugins()
    module_values = list(args.module)
    service_values = list(args.service)
    uses_values = list(args.uses)
    supplied = (
        module_values,
        service_values,
        uses_values,
        args.plugin,
        args.setting,
        args.portable,
        args.agents is not None,
    )
    if not args.non_interactive and not any(supplied):
        if not sys.stdin.isatty():
            raise WorkflowError("Sem terminal interativo; use --non-interactive ou forneça opções.")
        module_values, service_values, uses_values = _interactive_modules()

    for value in module_values:
        spec = parse_module(value)
        resolved = resolve_profiles(spec.profiles, registry)
        validate_kind(spec.kind, resolved, registry)
        previous = config.get("modules", {}).get(spec.name, {})
        config.setdefault("modules", {})[spec.name] = {
            **previous,
            "kind": spec.kind,
            "path": previous.get("path", spec.name),
            "requested_profiles": spec.profiles,
            "resolved_profiles": resolved,
            "settings": previous.get("settings", {}),
            "uses": previous.get("uses", []),
        }

    for value in service_values:
        name, profile_id = parse_service(value)
        resolved = resolve_profiles([profile_id], registry)
        if any(registry[item].category != "service" for item in resolved):
            raise WorkflowError(f"Perfil '{profile_id}' não é um serviço compartilhado.")
        config.setdefault("services", {})[name] = {
            "requested_profiles": [profile_id],
            "resolved_profiles": resolved,
            "settings": config.get("services", {}).get(name, {}).get("settings", {}),
        }

    for value in uses_values:
        module_name, service_names = parse_uses(value)
        if module_name not in config.get("modules", {}):
            raise WorkflowError(f"Módulo inexistente em --uses: {module_name}")
        missing = [name for name in service_names if name not in config.get("services", {})]
        if missing:
            raise WorkflowError(f"Serviços inexistentes em --uses: {', '.join(missing)}")
        config["modules"][module_name]["uses"] = service_names

    for value in args.setting:
        scope, key, setting_value = parse_setting(value)
        if scope in config.get("modules", {}):
            if key == "path":
                safe_path(root, setting_value)
                config["modules"][scope]["path"] = setting_value
            else:
                config["modules"][scope].setdefault("settings", {})[key] = setting_value
        elif scope in config.get("services", {}):
            config["services"][scope].setdefault("settings", {})[key] = setting_value
        elif scope == "project":
            config.setdefault("project", {})[key] = setting_value
        else:
            raise WorkflowError(f"Escopo desconhecido em --set: {scope}")

    plugins = list(dict.fromkeys(config.get("plugins", []) + list(args.plugin)))
    unknown_plugins = sorted(set(plugins) - set(plugin_registry))
    if unknown_plugins:
        raise WorkflowError(f"Plugins desconhecidos: {', '.join(unknown_plugins)}")
    config["plugins"] = plugins

    config = normalize_config(root, config)
    print(f"Plano: {len(config['modules'])} módulo(s), {len(config['services'])} serviço(s).")
    if (
        not args.non_interactive
        and not any(supplied)
        and input("Aplicar configuração? [s/N]: ").strip().lower() not in {"s", "sim", "y", "yes"}
    ):
        print("Nenhuma alteração aplicada.")
        return 0
    materialize(root, config)
    print(f"Configuração aplicada em {root}")
    print(f"Módulos: {', '.join(config.get('modules', {})) or 'nenhum'}")
    print(f"Serviços: {', '.join(config.get('services', {})) or 'nenhum'}")
    print(f"Plugins: {', '.join(config.get('plugins', [])) or 'nenhum'}")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    root = root_path(args.path)
    config = load_config(root)
    materialize(root, config)
    print("Commands, templates, rules e adaptadores sincronizados.")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    root = root_path(args.path)
    config = load_config(root)
    problems = check_materialized(root, config)
    status = config.get("project", {}).get("status", "desconhecido")
    print(f"Workflow: {config.get('workflow_version', 'desconhecido')}")
    print(f"Projeto: {config.get('project', {}).get('name', root.name)} ({status})")
    for module_name, module in config.get("modules", {}).items():
        print(f"[OK] módulo {module_name}: {', '.join(module.get('resolved_profiles', []))}")
    for service_name, service in config.get("services", {}).items():
        print(f"[OK] serviço {service_name}: {', '.join(service.get('resolved_profiles', []))}")
    for executable in ("git", "python"):
        available = shutil.which(executable) is not None
        print(f"[{'OK' if available else 'ERRO'}] ferramenta {executable}")
        if not available:
            problems.append(f"ferramenta ausente: {executable}")
    for problem in problems:
        print(f"[ERRO] {problem}")
    if status == "stack-undecided":
        print(
            "[AVISO] stack ainda não definida; PRDs podem ser criados, Tech Specs ficam bloqueadas."
        )
    return 1 if problems else 0


def cmd_validate(args: argparse.Namespace) -> int:
    root = root_path(args.path)
    load_config(root)
    feature = safe_path(root, args.feature)
    result = validate_feature(feature)
    for warning in result.warnings:
        print(f"AVISO: {warning}")
    for error in result.errors:
        print(f"ERRO: {error}")
    message = (
        "Planejamento válido."
        if result.ok
        else f"Planejamento inválido: {len(result.errors)} erro(s)."
    )
    print(message)
    return 0 if result.ok else 1


def cmd_upgrade(args: argparse.Namespace) -> int:
    root = root_path(args.path)
    config = load_config(root)
    previous = config.get("workflow_version", "desconhecida")
    materialize(root, config)
    print(f"Workflow atualizado de {previous} para {__version__}.")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    root = root_path(args.path)
    config = normalize_config(root, load_config(root))
    expected, _resolved = installation_plan(root, config)
    count = 0
    for relative, content in expected.items():
        path = safe_path(root, relative)
        if (relative.startswith("docs/") or relative == "MEMORY.md") and path.exists():
            continue
        if not path.exists():
            print(f"CRIAR {relative}")
            count += 1
        elif path.read_text(encoding="utf-8") != content:
            print(f"ATUALIZAR {relative}")
            count += 1
    print(f"{count} arquivo(s) novos ou divergentes; nenhuma alteração aplicada.")
    return 0


def cmd_profiles(args: argparse.Namespace) -> int:
    registry = load_profiles(root_path(args.path))
    by_category: dict[str, list[str]] = {}
    for profile in registry.values():
        by_category.setdefault(profile.category, []).append(profile.id)
    for category, values in sorted(by_category.items()):
        print(f"{category}: {', '.join(sorted(values))}")
    print("plugins: " + ", ".join(sorted(load_plugins())))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llm-workflow", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Inicializa o núcleo em um projeto")
    init.add_argument("path", nargs="?", default=".")
    init_targets = init.add_mutually_exclusive_group()
    init_targets.add_argument(
        "--agents",
        nargs="+",
        default=[],
        help="Adaptadores opcionais; padrão sem pastas de harness",
    )
    init_targets.add_argument("--portable", action="store_true", help="Somente núcleo portátil")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_init)

    configure = sub.add_parser("configure", help="Configura módulos, serviços e plugins")
    configure.add_argument("path", nargs="?", default=".")
    configure.add_argument("--module", action="append", default=[])
    configure.add_argument("--service", action="append", default=[])
    configure.add_argument("--uses", action="append", default=[])
    configure.add_argument("--set", dest="setting", action="append", default=[])
    configure.add_argument("--plugin", action="append", default=[])
    configure.add_argument("--non-interactive", action="store_true")
    configure.add_argument("--config", help="Importa uma configuração YAML declarativa")
    configure.add_argument("--ai", action="store_true", help="Propõe workflow via OpenRouter")
    configure.add_argument("--model", help="ID do modelo no OpenRouter")
    configure.add_argument(
        "--brief", help="Descrição do projeto enviada à LLM; não inclua segredos"
    )
    configure.add_argument("--answer", action="append", default=[], help="Resposta Q-01=texto")
    configure.add_argument(
        "--allow-paid", action="store_true", help="Autoriza envio e possível custo"
    )
    configure.add_argument("--max-tokens", type=int)
    configure_targets = configure.add_mutually_exclusive_group()
    configure_targets.add_argument("--agents", nargs="+", help="Seleciona adaptadores opcionais")
    configure_targets.add_argument(
        "--portable",
        action="store_true",
        help="Desativa adaptadores, preservando arquivos modificados",
    )
    configure.set_defaults(func=cmd_configure)

    for name, help_text, function in (
        ("sync", "Regenera arquivos e adaptadores", cmd_sync),
        ("doctor", "Diagnostica a instalação", cmd_doctor),
        ("upgrade", "Atualiza blocos gerenciados", cmd_upgrade),
        ("diff", "Mostra arquivos novos ou divergentes sem escrever", cmd_diff),
    ):
        command = sub.add_parser(name, help=help_text)
        command.add_argument("path", nargs="?", default=".")
        command.set_defaults(func=function)

    validate = sub.add_parser("validate", help="Valida documentos de uma feature")
    validate.add_argument("path")
    validate.add_argument("feature")
    validate.set_defaults(func=cmd_validate)

    profiles = sub.add_parser("profiles", help="Lista perfis e plugins disponíveis")
    profiles.add_argument("path", nargs="?", default=".")
    profiles.set_defaults(func=cmd_profiles)
    from .ai_cli import add_llm_parser

    add_llm_parser(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")
    try:
        args = build_parser().parse_args(argv)
        return args.func(args)
    except WorkflowError as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 2
    except (OSError, UnicodeError) as error:
        print(f"Erro de arquivo: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nOperação cancelada.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
