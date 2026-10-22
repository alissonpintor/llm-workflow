from __future__ import annotations

import hashlib
import json
from pathlib import Path, PureWindowsPath
from typing import Any

import yaml

from . import __version__

WORKFLOW_DIR = ".workflow"
CONFIG_FILE = "workflow.yaml"
LOCK_FILE = "workflow.lock"


class WorkflowError(RuntimeError):
    """User-facing configuration or installation error."""


def workflow_dir(root: Path) -> Path:
    return safe_path(root, WORKFLOW_DIR)


def safe_path(root: Path, relative: str) -> Path:
    """Contain generated files and reject symlink/junction escapes, on every OS."""
    windows = PureWindowsPath(relative)
    if not relative or windows.is_absolute() or windows.drive or ".." in windows.parts:
        raise WorkflowError(f"Caminho deve ser relativo e ficar dentro do projeto: {relative}")
    normalized = relative.replace("\\", "/")
    candidate = root / normalized
    if Path(normalized).is_absolute() or not candidate.resolve().is_relative_to(root.resolve()):
        raise WorkflowError(f"Caminho fora do projeto: {relative}")
    current = candidate
    while current != root:
        if current.is_symlink() or getattr(current, "is_junction", lambda: False)():
            raise WorkflowError(
                f"Link simbólico/junction não permitido em arquivo gerenciado: {relative}"
            )
        current = current.parent
    return candidate


def read_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise WorkflowError(f"YAML inválido em {path.name}.") from error
    if not isinstance(data, dict):
        raise WorkflowError(f"Esperado objeto YAML em {path.name}.")
    return data


def config_path(root: Path) -> Path:
    return safe_path(root, f"{WORKFLOW_DIR}/{CONFIG_FILE}")


def lock_path(root: Path) -> Path:
    return safe_path(root, f"{WORKFLOW_DIR}/{LOCK_FILE}")


def default_config(root: Path, agents: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "workflow_version": __version__,
        "project": {
            "name": root.resolve().name,
            "status": "stack-undecided",
            "architecture": "undecided",
        },
        "agents": {"targets": agents or ["agents", "grok", "zcode"]},
        "modules": {},
        "services": {},
        "plugins": [],
    }


def load_config(root: Path) -> dict[str, Any]:
    path = config_path(root)
    if not path.is_file():
        raise WorkflowError(
            f"Workflow não inicializado em {root}. Execute 'llm-workflow init {root}'."
        )
    return read_yaml(path)


def save_config(root: Path, config: dict[str, Any]) -> None:
    directory = workflow_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    config["workflow_version"] = __version__
    text = yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
    config_path(root).write_text(text, encoding="utf-8")


def load_lock(root: Path) -> dict[str, Any]:
    path = lock_path(root)
    if not path.is_file():
        return {}
    data = read_yaml(path)
    managed = data.get("managed_files", {})
    if not isinstance(managed, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in managed.items()
    ):
        raise WorkflowError("workflow.lock: managed_files inválido.")
    for relative in managed:
        safe_path(root, relative)
    return data


def save_lock(
    root: Path, managed_files: dict[str, str], resolved: dict[str, Any], config: dict[str, Any]
) -> None:
    payload = {
        "workflow_version": __version__,
        "config_sha256": config_digest(config),
        "managed_files": managed_files,
        "resolved": resolved,
    }
    lock_path(root).write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def config_digest(config: dict[str, Any]) -> str:
    canonical = json.dumps(config, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def file_digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
