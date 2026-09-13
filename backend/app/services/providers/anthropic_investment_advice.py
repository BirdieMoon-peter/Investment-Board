import json

import httpx

from app.core.settings import Settings
from app.schemas.investment_advice import InvestmentAdviceContext
from app.services.investment_advice_types import (
    GeneratedInvestmentAdvice,
    InvestmentAdviceProvider,
    InvestmentAdviceProviderError,
)

ANTHROPIC_VERSION = "2023-06-01"
SUPPORTED_ANTHROPIC_COMPATIBLE_PROVIDERS = {"anthropic", "dashscope_anthropic", "kimi"}
SUPPORTED_OPENAI_COMPATIBLE_PROVIDERS = {"openai", "openai_compatible"}
MESSAGES_PATH_SUFFIX = "/v1/messages"
CHAT_COMPLETIONS_PATH_SUFFIX = "/v1/chat/completions"


class AnthropicInvestmentAdviceProvider(InvestmentAdviceProvider):
    def __init__(
        self,
        *,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
    ):
        self._settings = settings
        self._client = httpx.Client(
            timeout=httpx.Timeout(settings.ai_http_timeout_seconds),
            transport=transport,
            follow_redirects=False,
        )

    def generate(self, context: InvestmentAdviceContext) -> GeneratedInvestmentAdvice:
        if not self._settings.ai_api_key:
            raise InvestmentAdviceProviderError("AI provider API key is not configured")

        try:
            response = self._client.post(
                _resolve_messages_url(self._settings.ai_api_url),
                headers={
                    "x-api-key": self._settings.ai_api_key,
                    "anthropic-version": ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
                json={
                    "model": self._settings.ai_model,
                    "max_tokens": self._settings.ai_max_output_tokens,
                    "temperature": self._settings.ai_temperature,
                    "system": _build_system_prompt(),
                    "messages": [
                        {
                            "role": "user",
                            "content": _build_user_prompt(context),
                        }
                    ],
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise InvestmentAdviceProviderError(_provider_error_message(exc)) from None

        return _parse_generated_advice(_extract_anthropic_text(_response_payload(response)))


class OpenAICompatibleInvestmentAdviceProvider(InvestmentAdviceProvider):
    def __init__(
        self,
        *,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
    ):
        self._settings = settings
        self._client = httpx.Client(
            timeout=httpx.Timeout(settings.ai_http_timeout_seconds),
            transport=transport,
            follow_redirects=False,
        )

    def generate(self, context: InvestmentAdviceContext) -> GeneratedInvestmentAdvice:
        if not self._settings.ai_api_key:
            raise InvestmentAdviceProviderError("AI provider API key is not configured")

        try:
            response = self._client.post(
                _resolve_chat_completions_url(self._settings.ai_api_url),
                headers={
                    "authorization": f"Bearer {self._settings.ai_api_key}",
                    "content-type": "application/json",
                },
                json={
                    "model": self._settings.ai_model,
                    "max_tokens": self._settings.ai_max_output_tokens,
                    "temperature": self._settings.ai_temperature,
                    "messages": [
                        {
                            "role": "system",
                            "content": _build_system_prompt(),
                        },
                        {
                            "role": "user",
                            "content": _build_user_prompt(context),
                        },
                    ],
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise InvestmentAdviceProviderError(_provider_error_message(exc)) from None

        return _parse_generated_advice(_extract_openai_text(_response_payload(response)))



def _provider_error_message(error: httpx.HTTPError) -> str:
    # Return only controlled messages: URLs, credentials and upstream bodies are private.
    if isinstance(error, httpx.HTTPStatusError):
        response = error.response
        status = response.status_code
        if status == 503:
            try:
                payload = response.json()
                details = payload.get("error") if isinstance(payload, dict) else None
                code = details.get("code") if isinstance(details, dict) else None
                message = details.get("message") if isinstance(details, dict) else None
            except ValueError:
                code = message = None
            if code == "auth_unavailable" or (
                isinstance(message, str) and message.strip().startswith("auth_unavailable:")
            ):
                return "AI provider has no available authenticated account (503); sign in to the provider again"
            return "AI provider is temporarily unavailable (503); retry later"
        messages = {
            401: "AI provider authentication failed (401); check credentials or sign in again",
            403: "AI provider access denied (403); check account and model permissions",
            404: "AI provider model or endpoint was not found (404); check configuration",
            429: "AI provider rate limit reached (429); retry later or check quota",
        }
        return messages.get(status, f"AI provider request failed ({status})")
    if isinstance(error, httpx.TimeoutException):
        return "AI provider request timed out; retry later"
    if isinstance(error, httpx.ConnectError):
        return "AI provider is unreachable; check that the service is running and the connection is available"
    return "AI provider request failed; check the service connection and retry"


def build_investment_advice_provider(
    *,
    settings: Settings,
    transport: httpx.BaseTransport | None = None,
) -> InvestmentAdviceProvider:
    if settings.ai_provider in SUPPORTED_ANTHROPIC_COMPATIBLE_PROVIDERS:
        return AnthropicInvestmentAdviceProvider(settings=settings, transport=transport)
    if settings.ai_provider in SUPPORTED_OPENAI_COMPATIBLE_PROVIDERS:
        return OpenAICompatibleInvestmentAdviceProvider(settings=settings, transport=transport)
    raise InvestmentAdviceProviderError(f"Unsupported AI provider: {settings.ai_provider}")


def _build_system_prompt() -> str:
    return (
        "You are an investment analysis assistant for a personal investment board. "
        "You must respond with valid JSON only and no markdown. "
        "Use exactly these fields: recommendation, confidence, summary, thesis_points, risk_points, "
        "position_notes, recent_catalysts, full_analysis, warnings, disclaimer. "
        "recommendation must be one of buy, accumulate, hold, trim, sell, watch. "
        "confidence must be one of high, medium, low. "
        "Each list field must be an array of short strings. "
        "full_analysis should be a long-form explanation grounded in the provided context. "
        "Do not claim certainty. Include a clear disclaimer that this is model-generated advisory content, not financial advice."
    )


def _build_user_prompt(context: InvestmentAdviceContext) -> str:
    return json.dumps(context.model_dump(mode="json"), ensure_ascii=False, indent=2)


def _resolve_messages_url(url: str) -> str:
    normalized = url.rstrip("/")
    if normalized.endswith(MESSAGES_PATH_SUFFIX):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/messages"
    return f"{normalized}{MESSAGES_PATH_SUFFIX}"


def _resolve_chat_completions_url(url: str) -> str:
    normalized = url.rstrip("/")
    if normalized.endswith(CHAT_COMPLETIONS_PATH_SUFFIX):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    return f"{normalized}{CHAT_COMPLETIONS_PATH_SUFFIX}"


def canonical_provider_destination(provider: str, api_url: str) -> tuple[str, str]:
    if provider in SUPPORTED_ANTHROPIC_COMPATIBLE_PROVIDERS:
        return ('anthropic', str(httpx.URL(_resolve_messages_url(api_url))))
    if provider in SUPPORTED_OPENAI_COMPATIBLE_PROVIDERS:
        return ('openai', str(httpx.URL(_resolve_chat_completions_url(api_url))))
    raise ValueError('Unsupported AI provider')


def _response_payload(response: httpx.Response) -> dict:
    try:
        payload = response.json()
    except ValueError:
        raise InvestmentAdviceProviderError('AI provider returned invalid JSON') from None
    if not isinstance(payload, dict):
        raise InvestmentAdviceProviderError('AI provider returned invalid content payload')
    return payload


def _extract_anthropic_text(payload: dict) -> str:
    content = payload.get("content")
    if not isinstance(content, list):
        raise InvestmentAdviceProviderError("AI provider returned invalid content payload")

    parts: list[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
            parts.append(item["text"])

    text = "\n".join(part for part in parts if part.strip()).strip()
    if not text:
        raise InvestmentAdviceProviderError("AI provider returned empty text content")
    return text


def _extract_openai_text(payload: dict) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise InvestmentAdviceProviderError("AI provider returned invalid choices payload")

    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise InvestmentAdviceProviderError("AI provider returned invalid message payload")

    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                parts.append(item["text"])
        text = "\n".join(part for part in parts if part.strip()).strip()
        if text:
            return text

    raise InvestmentAdviceProviderError("AI provider returned empty text content")


def _parse_generated_advice(text: str) -> GeneratedInvestmentAdvice:
    parsed = _parse_json_payload(text)
    return GeneratedInvestmentAdvice(
        recommendation=_require_choice(
            parsed,
            key="recommendation",
            allowed={"buy", "accumulate", "hold", "trim", "sell", "watch"},
        ),
        confidence=_require_choice(
            parsed,
            key="confidence",
            allowed={"high", "medium", "low"},
        ),
        summary=_require_string(parsed, "summary"),
        thesis_points=_require_string_list(parsed, "thesis_points"),
        risk_points=_require_string_list(parsed, "risk_points"),
        position_notes=_require_string_list(parsed, "position_notes"),
        recent_catalysts=_require_string_list(parsed, "recent_catalysts"),
        full_analysis=_require_string(parsed, "full_analysis"),
        warnings=_optional_string_list(parsed, "warnings"),
        disclaimer=_require_string(parsed, "disclaimer"),
    )


def _parse_json_payload(text: str) -> dict:
    normalized = text.strip()
    if normalized.startswith("```"):
        normalized = normalized.strip("`")
        if normalized.startswith("json"):
            normalized = normalized[4:].strip()

    candidates = [normalized]
    object_start = normalized.find("{")
    object_end = normalized.rfind("}")
    if object_start != -1 and object_end != -1 and object_end > object_start:
        candidates.append(normalized[object_start : object_end + 1].strip())

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise InvestmentAdviceProviderError("AI provider returned invalid JSON")


def _require_string(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InvestmentAdviceProviderError(f"AI provider returned invalid {key}")
    return value.strip()


def _require_string_list(payload: dict, key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise InvestmentAdviceProviderError(f"AI provider returned invalid {key}")
    items = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if not items:
        raise InvestmentAdviceProviderError(f"AI provider returned empty {key}")
    return items


def _optional_string_list(payload: dict, key: str) -> list[str]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise InvestmentAdviceProviderError(f"AI provider returned invalid {key}")
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _require_choice(payload: dict, *, key: str, allowed: set[str]) -> str:
    value = _require_string(payload, key).lower()
    if value not in allowed:
        raise InvestmentAdviceProviderError(f"AI provider returned unsupported {key}")
    return value
