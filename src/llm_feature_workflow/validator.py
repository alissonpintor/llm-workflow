from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

REQUIREMENT = re.compile(r"\b(?:RF|NFR)-\d{2,}\b")
TASK = re.compile(r"^- \[[ xX]\] (\d+)\.0\s+", re.MULTILINE)
PLACEHOLDER = re.compile(r"\b(?:TBD|TODO)\b|\[(?:preencher|nome|descri[cç][aã]o|item)\]", re.I)

HEADINGS = {
    "domain-assessment.md": [
        "Escopo e Recomendação",
        "Evidências do Usuário",
        "Padrões, Benefícios e Custos",
        "Alternativa Mais Simples",
        "Perguntas Abertas",
        "Aprovação",
    ],
    "discovery.md": ["Evidências e Fontes", "Casos de Borda Candidatos", "Perguntas Abertas"],
    "prd.md": [
        "Problema e Evidências",
        "Requisitos Funcionais",
        "Requisitos Não Funcionais",
        "Casos de Borda e Exceções",
        "Critérios de Aceite",
    ],
    "techspec.md": [
        "Cobertura dos Requisitos",
        "Casos de Borda, Concorrência e Modos de Falha",
        "Segurança e Privacidade",
        "Estratégia de Testes",
        "Decisões Técnicas",
    ],
    "tasks.md": ["Estado do Planejamento", "Matriz de Tarefas", "Cobertura Consolidada"],
}


def section(text: str, title: str) -> str:
    match = re.search(rf"^## {re.escape(title)}\s*$", text, re.MULTILINE)
    if not match:
        return ""
    return re.split(r"^## ", text[match.end() :], maxsplit=1, flags=re.MULTILINE)[0]


def has_cycle(graph: dict[str, set[str]]) -> bool:
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in done:
            return False
        visiting.add(node)
        if any(visit(dep) for dep in graph.get(node, set())):
            return True
        visiting.remove(node)
        done.add(node)
        return False

    return any(visit(node) for node in graph)


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_feature(directory: Path) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    required = ["discovery.md", "prd.md", "domain-assessment.md", "techspec.md", "tasks.md"]
    texts: dict[str, str] = {}
    for name in required:
        path = directory / name
        if not path.is_file():
            errors.append(f"arquivo obrigatório ausente: {name}")
            texts[name] = ""
        else:
            texts[name] = path.read_text(encoding="utf-8")
        for heading in HEADINGS[name]:
            if not re.search(rf"^## {re.escape(heading)}\s*$", texts[name], re.MULTILINE):
                errors.append(f"{name}: seção ausente: {heading}")

    for review in ("prd-review.md", "techspec-review.md"):
        path = directory / "reviews" / review
        if not path.is_file():
            errors.append(f"review ausente: reviews/{review}")
        elif not re.search(r"^-?\s*Status:\s*APROVADO\s*$", path.read_text(encoding="utf-8"), re.M):
            errors.append(f"review não aprovado: reviews/{review}")

    domain = texts["domain-assessment.md"]
    if not re.search(r"^- Status: APROVADO\s*$", domain, re.M):
        errors.append("domain-assessment.md: aprovação humana pendente")
    if not re.search(r"^- Perguntas bloqueantes: 0\s*$", domain, re.M):
        errors.append("domain-assessment.md: perguntas bloqueantes pendentes")
    if not re.search(
        r"^- Recomendação: (simple_design|strategic_ddd|selective_ddd)\s*$", domain, re.M
    ):
        errors.append("domain-assessment.md: recomendação ausente ou contexto insuficiente")
    if not re.search(r"\b(BRIEF|Q-\d{2,}|EVD-\d{2,})\b", section(domain, "Evidências do Usuário")):
        errors.append("domain-assessment.md: fonte do usuário ausente")

    requirements = set(REQUIREMENT.findall(texts["prd.md"]))
    if not requirements:
        errors.append("prd.md: nenhum RF-* ou NFR-* encontrado")
    for name in ("techspec.md", "tasks.md"):
        missing = sorted(item for item in requirements if item not in texts[name])
        if missing:
            errors.append(f"{name}: requisitos sem cobertura: {', '.join(missing)}")

    if not re.search(r"\bAC-\d{2,}\b", texts["prd.md"]):
        errors.append("prd.md: nenhum AC-* encontrado")
    if not re.search(r"\bDEC-\d{2,}\b", texts["techspec.md"]):
        errors.append("techspec.md: nenhuma DEC-* encontrada")
    if not re.search(r"\bTEST-\d{2,}\b", texts["techspec.md"]):
        errors.append("techspec.md: nenhum TEST-* encontrado")

    missing_acceptance = sorted(
        req
        for req in requirements
        if req.startswith("RF-") and req not in section(texts["prd.md"], "Critérios de Aceite")
    )
    if missing_acceptance:
        errors.append("prd.md: RF sem critério de aceite: " + ", ".join(missing_acceptance))

    for prefix, name, title in (
        ("RF", "prd.md", "Requisitos Funcionais"),
        ("NFR", "prd.md", "Requisitos Não Funcionais"),
        ("AC", "prd.md", "Critérios de Aceite"),
        ("DEC", "techspec.md", "Decisões Técnicas"),
        ("TEST", "techspec.md", "Estratégia de Testes"),
    ):
        body = section(texts[name], title)
        definitions = re.findall(
            rf"^(?:#+\s+|[-*]\s+\*{{0,2}}|\|\s*)({prefix}-\d{{2,}})\b", body, re.MULTILINE
        )
        if len(set(definitions)) != len(definitions):
            errors.append(f"{name}: definição {prefix}-* duplicada")

    for requirement in sorted(requirements):
        coverage = section(texts["techspec.md"], "Cobertura dos Requisitos")
        rows = [line for line in coverage.splitlines() if requirement in line]
        if not any(
            re.search(r"DEC-\d{2,}", row) and re.search(r"TEST-\d{2,}", row) for row in rows
        ):
            errors.append(f"techspec.md: {requirement} sem DEC/TEST na matriz de cobertura")

    task_ids = TASK.findall(texts["tasks.md"])
    if not task_ids:
        errors.append("tasks.md: nenhuma task no formato '- [ ] N.0 Título'")
    if len(set(task_ids)) != len(task_ids):
        errors.append("tasks.md: IDs de task duplicados")
    graph: dict[str, set[str]] = {}
    task_texts: dict[str, str] = {}
    tech_ids = set(re.findall(r"\b(?:DEC|TEST)-\d{2,}\b", texts["techspec.md"]))
    for task_id in task_ids:
        task_path = directory / f"{task_id}_task.md"
        if not task_path.is_file():
            errors.append(f"arquivo de task ausente: {task_id}_task.md")
        else:
            task_text = task_path.read_text(encoding="utf-8")
            task_texts[task_id] = task_text
            if "## Plano de Verificação" not in task_text:
                errors.append(f"{task_id}_task.md: Plano de Verificação ausente")
            if not re.search(rf"^# Tarefa {task_id}\.0\b", task_text, re.MULTILINE):
                errors.append(f"{task_id}_task.md: título incorreto")
            dependencies = re.search(r"^- Dependências:[ \t]*(.+)$", task_text, re.MULTILINE)
            if not dependencies:
                errors.append(f"{task_id}_task.md: dependências não declaradas")
                graph[task_id] = set()
            else:
                value = dependencies.group(1).strip()
                graph[task_id] = set(re.findall(r"\b(\d+)\.0\b", value))
                if not graph[task_id] and value.lower() not in {"nenhuma", "—", "n/a"}:
                    errors.append(f"{task_id}_task.md: formato de dependências inválido")
            for prefix in ("DEC", "TEST"):
                ids = set(re.findall(rf"\b{prefix}-\d{{2,}}\b", task_text))
                if not ids:
                    errors.append(f"{task_id}_task.md: sem referência {prefix}-*")
                if ids - tech_ids:
                    errors.append(
                        f"{task_id}_task.md: IDs inexistentes: {', '.join(sorted(ids - tech_ids))}"
                    )
            if PLACEHOLDER.search(task_text):
                errors.append(f"{task_id}_task.md: placeholder/TBD não resolvido")

    for task_id, dependencies in graph.items():
        if dependencies - set(task_ids):
            errors.append(f"{task_id}_task.md: dependência inexistente")
    if has_cycle(graph):
        errors.append("tasks.md: ciclo de dependência")
    joined_tasks = "\n".join(task_texts.values())
    for requirement in sorted(requirements):
        if requirement not in joined_tasks:
            errors.append(f"tasks: {requirement} sem task individual")

    ui = re.search(r"^- UI/UX aplicável:[ \t]*(SIM|NÃO|NAO)\s*$", texts["tasks.md"], re.M | re.I)
    if not ui:
        errors.append("tasks.md: UI/UX aplicável não definido como SIM/NÃO")
    elif ui.group(1).upper() == "SIM" and not (directory / "uiux-spec.md").is_file():
        errors.append("uiux-spec.md obrigatório")

    for name, label in (
        ("prd.md", "Perguntas bloqueantes"),
        ("techspec.md", "Perguntas técnicas bloqueantes"),
    ):
        if not re.search(rf"^- {label}:[ \t]*0\s*$", texts[name], re.MULTILINE):
            errors.append(f"{name}: declare '{label}: 0' para liberar o planejamento")

    if "Responsável pelo release: gate final do PRD" not in texts["tasks.md"]:
        errors.append("tasks.md: release deve pertencer ao gate final do PRD")

    for name, text in texts.items():
        if text and PLACEHOLDER.search(text):
            errors.append(f"{name}: placeholder/TBD não resolvido")

    return ValidationResult(tuple(errors), tuple(warnings))
