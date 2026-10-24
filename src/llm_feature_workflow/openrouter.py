"""A bounded OpenRouter transport; no tools, redirects, retries or arbitrary endpoints."""

from __future__ import annotations

import json
import math
import re
from typing import Any

import httpx
from pydantic import ValidationError

from .ai_models import (
    ContinuationResponse,
    GenerationResponse,
    Proposal,
    generation_schema,
    valid_model_id,
)
from .config import WorkflowError

BASE_URL = "https://openrouter.ai/api/v1"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024

# Only schema-owned labels and known validator messages may enter diagnostics.
# Pydantic's full errors can include input values, JSON excerpts and unknown extra keys.
_SCHEMA = generation_schema()
_FIELD_NAMES = {
    name
    for node in [_SCHEMA, *_SCHEMA.get("$defs", {}).values()]
    for name in node.get("properties", {})
}
_VALIDATOR_MESSAGES = {
    "evidências de domínio com IDs duplicados",
    "padrão sem referência a evidência existente",
    "contexto insuficiente exige perguntas e não autoriza padrões",
    "recomendação conclusiva exige evidência e ausência de pendências",
    "design simples não deve prescrever padrões DDD",
    "DDD estratégico não autoriza padrões táticos",
    "DDD seletivo exige padrão tático justificado",
    "avaliação de domínio duplicada no mesmo escopo",
    "avaliações de domínio precisam cobrir todos os módulos propostos",
    "avaliação referencia pergunta bloqueante inexistente",
    "use caminhos relativos com /",
    "caminho reservado ou fora do módulo",
    "comandos devem ter uma única linha sem controles",
    "cada módulo precisa de regras de design, segurança e testes",
    "uma proposta sem perguntas deve conter módulos",
    *(f"IDs duplicados em {field}" for field in ("profiles", "modules", "services", "questions")),
}
_ERROR_LABELS = {
    "missing": "campo obrigatório ausente",
    "extra_forbidden": "campo adicional não permitido",
    "string_too_short": "texto abaixo do tamanho mínimo",
    "string_too_long": "texto acima do tamanho máximo",
    "string_pattern_mismatch": "formato de texto inválido",
    "too_short": "lista abaixo do tamanho mínimo",
    "too_long": "lista acima do tamanho máximo",
    "literal_error": "opção fora das permitidas",
    "list_type": "lista esperada",
    "string_type": "texto esperado",
    "model_type": "objeto esperado",
    "union_tag_invalid": "tipo de resposta fora das opções permitidas",
    "union_tag_not_found": "tipo de resposta obrigatório ausente",
}


def _schema_diagnostic(error: ValidationError) -> str:
    details = []
    for item in error.errors(include_url=False, include_input=False)[:5]:
        path = ""
        for part in item["loc"]:
            if type(part) is int and 0 <= part <= 1000:
                path += f"[{part}]"
            else:
                label = (
                    part if isinstance(part, str) and part in _FIELD_NAMES else "[campo omitido]"
                )
                path += ("." if path else "") + label
        reason = _ERROR_LABELS.get(item["type"], "restrição do contrato não atendida")
        if item["type"] == "value_error":
            known = str(item.get("ctx", {}).get("error", ""))
            if known in _VALIDATOR_MESSAGES:
                reason = known
        details.append(f"{path or 'proposta'}: {reason}")
    if error.error_count() > 5:
        details.append(f"mais {error.error_count() - 5} erro(s)")
    return "; ".join(details)


def _generation_failure(message: str, envelope: dict) -> WorkflowError:
    usage = envelope.get("usage")
    counters = []
    if isinstance(usage, dict):
        details = usage.get("completion_tokens_details")
        values = [("saída", usage.get("completion_tokens"))]
        if isinstance(details, dict):
            values.append(("raciocínio", details.get("reasoning_tokens")))
        for label, value in values:
            if type(value) is int and 0 <= value <= 10**12:
                counters.append(f"{label}={value}")
    tokens = " Contadores informados: " + ", ".join(counters) + "." if counters else ""
    return WorkflowError(
        message + tokens + " Nada foi salvo ou aplicado. Não houve retry automático; "
        "a chamada pode ter sido cobrada."
    )


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
        continuation = isinstance(context.get("answers"), list) and bool(context["answers"])
        if continuation:
            system += (
                "\nRETOMADA APÓS RESPOSTAS: use result.kind=proposal e o formato completo. "
                "Não devolva respostas como perguntas. Se surgiu um bloqueio novo, registre-o "
                "em questions com ID novo e deixe os arrays de rascunho vazios; nunca invente "
                "dados para completar a proposta. Se não há bloqueios, questions deve ser []."
            )
        schema = generation_schema(continuation=continuation)
        sources = context.get("domain_sources", {})
        quotes = []
        if isinstance(sources, dict):
            for text in sources.values():
                if not isinstance(text, str):
                    continue
                for sentence in re.split(r"(?<=[.!?])\s+|\n", text):
                    for start in range(0, len(sentence), 2000):
                        excerpt = sentence[start : start + 2000].strip()
                        if len(excerpt) >= 10 and excerpt not in quotes:
                            quotes.append(excerpt)
        if quotes:
            schema["$defs"]["DomainEvidence"]["properties"]["quote"]["enum"] = quotes[:80]
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
                    "schema": schema,
                },
            },
        }
        envelope = self._request("POST", "/chat/completions", payload)
        choices = envelope.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise _generation_failure("OpenRouter retornou choices ausente ou inválido.", envelope)
        choice = choices[0]
        if choice.get("finish_reason") == "length":
            raise _generation_failure(
                "Resposta truncada por limite de tokens "
                f"(finish_reason=length; limite={max_tokens}). "
                "Tokens de raciocínio também podem consumir esse limite. "
                "Antes de outra geração, avalie reduzir o escopo, outro modelo ou "
                "--max-tokens 16000 (se o limite atual for menor); aumentar pode elevar o custo.",
                envelope,
            )
        message = choice.get("message")
        if choice.get("finish_reason") == "content_filter" or (
            isinstance(message, dict) and message.get("refusal")
        ):
            raise _generation_failure("Resposta recusada pelo modelo/provedor.", envelope)
        if choice.get("finish_reason") != "stop":
            raise _generation_failure("Geração interrompida sem conclusão normal.", envelope)
        if not isinstance(message, dict):
            raise _generation_failure("OpenRouter retornou message ausente ou inválido.", envelope)
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise _generation_failure(
                "Resposta sem conteúdo final JSON. "
                "Tokens de raciocínio não constituem uma proposta.",
                envelope,
            )
        if self._key and self._key in content:
            raise WorkflowError("Resposta descartada por conter credencial. Nada foi salvo.")
        try:
            response_model = ContinuationResponse if continuation else GenerationResponse
            response = response_model.model_validate_json(content)
            proposal = response.to_proposal()
        except ValidationError as error:
            if any(item["type"] == "json_invalid" for item in error.errors(include_input=False)):
                raise _generation_failure(
                    "O modelo retornou JSON inválido, apesar do JSON Schema solicitado. "
                    "Não houve reparo automático. Revise o contexto ou escolha outro modelo.",
                    envelope,
                ) from None
            raise _generation_failure(
                "A resposta não atende ao schema da proposta. " + _schema_diagnostic(error) + ". "
                "Revise o contexto ou escolha outro modelo; os valores recebidos foram omitidos.",
                envelope,
            ) from None
        if self._key and self._key in proposal.model_dump_json():
            raise WorkflowError("Resposta descartada por conter credencial. Nada foi salvo.")
        usage = envelope.get("usage", {})
        metadata = {"requested_model": model}
        # Keep only scalar usage counters; no prompts, reasoning or raw provider responses.
        if isinstance(usage, dict):
            for field in ("prompt_tokens", "completion_tokens", "total_tokens", "cost"):
                value = usage.get(field)
                if type(value) in (int, float) and 0 <= value <= 1e12 and math.isfinite(value):
                    metadata[field] = value
        return proposal, metadata
