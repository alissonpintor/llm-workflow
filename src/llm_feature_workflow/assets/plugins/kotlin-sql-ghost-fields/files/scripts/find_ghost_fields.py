#!/usr/bin/env python3
"""Detecta leituras Kotlin de campos ausentes dos SELECTs no mesmo arquivo.

O resultado é heurístico e precisa de validação contextual. Use ``--campos`` para
fornecer documentos canônicos e ``--out`` para manter o relatório fora do repo.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

INDEX_GET = re.compile(r'\[\s*"([A-Z][A-Z0-9_]+)"\s*\]')
DOT_GET = re.compile(r'\.\s*(?:get|getValue)\(\s*"([A-Z][A-Z0-9_]+)"\s*(,)?')
RAW_STRING = re.compile(r'"""(.*?)"""', re.DOTALL)
LINE_STRING = re.compile(r'"(?:[^"\\\n]|\\.)*"')
SELECT_KEYWORD = re.compile(r"\bSELECT\b", re.IGNORECASE)
UPPER_IDENTIFIER = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")
SQL_ALIAS = re.compile(r"\bAS\s+([A-Z][A-Z0-9_]+)", re.IGNORECASE)


@dataclass(frozen=True)
class Candidate:
    file: Path
    line: int
    field: str
    has_default: bool
    in_reference: bool | None

    @property
    def classification(self) -> str:
        if self.in_reference is True:
            return "campo conhecido — rastrear origem da row"
        if self.has_default:
            return "fallback possivelmente morto"
        return "chave fora dos SELECTs do arquivo"


def load_reference(paths: list[Path]) -> set[str]:
    fields: set[str] = set()
    for path in paths:
        fields.update(UPPER_IDENTIFIER.findall(path.read_text(encoding="utf-8")))
    return fields


def sql_blocks(source: str) -> list[str]:
    blocks: list[str] = []

    def capture_raw(match: re.Match[str]) -> str:
        blocks.append(match.group(1))
        return " " * len(match.group(0))

    without_raw = RAW_STRING.sub(capture_raw, source)
    blocks.extend(match.group(0)[1:-1] for match in LINE_STRING.finditer(without_raw))
    return [block for block in blocks if SELECT_KEYWORD.search(block)]


def selected_columns(source: str) -> set[str]:
    columns: set[str] = set()
    for block in sql_blocks(source):
        columns.update(UPPER_IDENTIFIER.findall(block))
        columns.update(alias.upper() for alias in SQL_ALIAS.findall(block))
    return columns


def scan_file(path: Path, reference: set[str] | None) -> list[Candidate]:
    source = path.read_text(encoding="utf-8")
    columns = selected_columns(source)
    if not columns:
        return []
    candidates: list[Candidate] = []
    seen: set[tuple[int, str]] = set()

    for expression, default_from_group in ((INDEX_GET, False), (DOT_GET, True)):
        for match in expression.finditer(source):
            field = match.group(1)
            if field in columns:
                continue
            line = source[: match.start()].count("\n") + 1
            if (line, field) in seen:
                continue
            seen.add((line, field))
            if default_from_group:
                has_default = match.group(2) is not None
            else:
                end = source.find("\n", match.end())
                remainder = source[match.end() : len(source) if end == -1 else end]
                has_default = remainder.lstrip().startswith("?:")
            candidates.append(
                Candidate(
                    file=path,
                    line=line,
                    field=field,
                    has_default=has_default,
                    in_reference=None if reference is None else field in reference,
                )
            )
    return candidates


def collect(root: Path, include_tests: bool, reference: set[str] | None) -> list[Candidate]:
    result: list[Candidate] = []
    for path in sorted(root.rglob("*.kt")):
        if not include_tests and any(
            part.lower().startswith("test") for part in path.relative_to(root).parts
        ):
            continue
        result.extend(scan_file(path, reference))
    return result


def report(root: Path, candidates: list[Candidate], reference_enabled: bool) -> str:
    lines = [
        f"# Campos fantasma — rascunho ({datetime.now().astimezone():%Y-%m-%d %H:%M})",
        "",
        f"- Pasta: `{root}`",
        f"- Candidatos: **{len(candidates)}**",
        f"- Referência canônica aplicada: **{'sim' if reference_enabled else 'não'}**",
        "",
        "| arquivo:linha | campo | default | referência | classificação provável |",
        "|---|---|---|---|---|",
    ]
    for item in candidates:
        reference = "—" if item.in_reference is None else str(item.in_reference)
        lines.append(
            f"| {item.file.as_posix()}:{item.line} | `{item.field}` | "
            f"{'sim' if item.has_default else 'não'} | {reference} | {item.classification} |"
        )
    lines.extend(
        [
            "",
            "> Valide origem da row, aliases, consultas em outros módulos e "
            "mapas/payloads antes de concluir.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--campos", type=Path, nargs="*", default=[])
    parser.add_argument("--incluir-testes", action="store_true")
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error(f"pasta alvo não é diretório: {args.root}")
    reference = load_reference(args.campos) if args.campos else None
    candidates = collect(args.root, args.incluir_testes, reference)
    output = args.out or Path(f"ghost-fields-{datetime.now().astimezone():%Y%m%d-%H%M}.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report(args.root, candidates, reference is not None), encoding="utf-8")
    print(f"{len(candidates)} candidatos -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
