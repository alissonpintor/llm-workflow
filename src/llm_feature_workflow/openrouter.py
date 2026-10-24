"""A bounded OpenRouter transport; no tools, redirects, retries or arbitrary endpoints."""

from __future__ import annotations

import json
import math
from typing import Any

import httpx
from pydantic import ValidationError

from .ai_models import Proposal, valid_model_id
from .config import WorkflowError

BASE_URL = "https://openrouter.ai/api/v1"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class OpenRouter:
    def __init__(self, *, api_key: str = "", transport: httpx.BaseTransport | None = None):
        self._key = api_key
        self._transport = transport

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict:
        headers = {"Content-Type": "application/json"}
        if method == "POST":
            if (
                not self._key
                or not self._key.isascii()
                or any(ord(c) < 33 or ord(c) == 127 for c in self._key)
            ):
                raise WorkflowError("Defina OPENROUTER_API_KEY válida; a chave não será salva.")
            headers["Authorization"] = f"Bearer {self._key}"
        try:
            with (
                httpx.Client(
                    transport=self._transport, timeout=120, follow_redirects=False, trust_env=False
                ) as client,
                client.stream(method, BASE_URL + path, headers=headers, json=body) as response,
            ):
                if response.status_code != 200:
                    # Never display bodies: providers may echo user content or secrets.
                    raise WorkflowError(
                        f"OpenRouter HTTP {response.status_code}. Verifique chave, saldo, "
                        "modelo e suporte a JSON Schema. Não houve retry automático."
                    )
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_RESPONSE_BYTES:
                        raise WorkflowError("Resposta OpenRouter excedeu o limite permitido.")
            result = json.loads(data)
        except httpx.HTTPError:
            raise WorkflowError(
                "Falha de conexão/timeout no OpenRouter. Não houve retry; uma geração "
                "interrompida pode ter sido cobrada."
            ) from None
        except (ValueError, UnicodeError, RecursionError):
            raise WorkflowError("OpenRouter retornou resposta JSON inválida.") from None
        if not isinstance(result, dict) or "error" in result:
            raise WorkflowError("OpenRouter retornou erro ou envelope inesperado.")
        return result

    def models(self, query: str = "") -> list[dict[str, Any]]:
        data = self._request("GET", "/models").get("data")
        if not isinstance(data, list):
            raise WorkflowError("Catálogo OpenRouter inválido.")
        return [
            {"id": row["id"], "name": row.get("name", row["id"])}
            for row in data
            if isinstance(row, dict)
            and isinstance(row.get("id"), str)
            and query.lower() in (row["id"] + str(row.get("name", ""))).lower()
            and isinstance(row.get("supported_parameters"), list)
            and "structured_outputs" in row.get("supported_parameters", [])
        ]

    def generate(
        self, *, model: str, system: str, context: dict[str, Any], max_tokens: int = 8000
    ) -> tuple[Proposal, dict[str, Any]]:
        try:
            valid_model_id(model)
        except ValueError as error:
            raise WorkflowError(str(error)) from None
        if type(max_tokens) is not int or not 512 <= max_tokens <= 16000:
            raise WorkflowError("max_tokens deve estar entre 512 e 16000.")
        if self._key and (
            self._key in json.dumps(context, ensure_ascii=False) or self._key in system
        ):
            raise WorkflowError("O contexto contém a credencial. Remova-a antes de continuar.")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
            ],
            "max_tokens": max_tokens,
            "stream": False,
            "provider": {
                "require_parameters": True,
                "allow_fallbacks": False,
                "data_collection": "deny",
            },
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "workflow_proposal",
                    "strict": True,
                    "schema": Proposal.model_json_schema(),
                },
            },
        }
        envelope = self._request("POST", "/chat/completions", payload)
        try:
            choice = envelope["choices"][0]
            content = choice["message"]["content"]
            if (
                choice.get("finish_reason") != "stop"
                or not isinstance(content, str)
                or choice["message"].get("refusal")
            ):
                raise ValueError("incomplete response")
            if self._key and self._key in content:
                raise WorkflowError("Resposta descartada por conter credencial. Nada foi salvo.")
            proposal = Proposal.model_validate_json(content)
            if self._key and self._key in proposal.model_dump_json():
                raise WorkflowError("Resposta descartada por conter credencial. Nada foi salvo.")
        except (KeyError, IndexError, TypeError, ValueError, ValidationError):
            raise WorkflowError(
                "Resposta incompleta, recusada ou fora do schema. Nada foi aplicado; "
                "não houve retry automático."
            ) from None
        usage = envelope.get("usage", {})
        metadata = {"requested_model": model}
        # Keep only scalar usage counters; no prompts, reasoning or raw provider responses.
        if isinstance(usage, dict):
            for field in ("prompt_tokens", "completion_tokens", "total_tokens", "cost"):
                value = usage.get(field)
                if type(value) in (int, float) and 0 <= value <= 1e12 and math.isfinite(value):
                    metadata[field] = value
        return proposal, metadata
