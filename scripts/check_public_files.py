"""Audit tracked public files without printing potential secret values.

This is a focused pre-publication safeguard, not a complete secret scanner.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

RULES = {
    "OpenRouter key": re.compile(r"\bsk-or-v1-[A-Za-z0-9]{32,}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "credential in URL": re.compile(r"https?://[^\s/@:]+:[^\s/@]+@"),
    "local personal path": re.compile(r"[A-Za-z]:\\(?:Users|Projetos)\\[^\s`\"']+"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-untracked", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    command = ["git", "ls-files", "-z", "--cached"]
    if args.include_untracked:
        command.extend(["--others", "--exclude-standard"])
    result = subprocess.run(command, cwd=root, check=True, capture_output=True)
    paths = [value.decode("utf-8") for value in result.stdout.split(b"\0") if value]
    problems: list[str] = []
    for relative in paths:
        path = root / relative
        name = path.name.lower()
        if (
            (name.startswith(".env") and name != ".env.example")
            or name
            in {
                "id_rsa",
                "id_ed25519",
                ".netrc",
                ".pypirc",
            }
            or path.suffix.lower() in {".key", ".p12", ".pfx"}
        ):
            problems.append(f"{relative}: sensitive filename")
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            problems.append(f"{relative}: binary requires manual review")
            continue
        for number, line in enumerate(content.splitlines(), 1):
            for label, pattern in RULES.items():
                if pattern.search(line):
                    problems.append(f"{relative}:{number}: {label}")
    for problem in problems:
        print(problem)
    print(f"Public-file audit: {len(paths)} candidate files, {len(problems)} finding(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
