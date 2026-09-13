import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[3] / "investment_board.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATABASE_PATH}"
DEFAULT_AI_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_AI_MODEL = "claude-sonnet-4-6"
DEFAULT_AI_HTTP_TIMEOUT_SECONDS = 30.0
OPENAI_COMPATIBLE_AI_HTTP_TIMEOUT_SECONDS = 120.0
DASHSCOPE_AI_HTTP_TIMEOUT_SECONDS = 300.0
DASHSCOPE_ANTHROPIC_BASE_URL = "https://coding.dashscope.aliyuncs.com/apps/anthropic"
DASHSCOPE_KIMI_MODEL = "kimi-k2.5"
DASHSCOPE_COMPATIBLE_PROVIDERS = {"dashscope_anthropic", "kimi"}
OPENAI_COMPATIBLE_PROVIDERS = {"openai", "openai_compatible"}
DEFAULT_LOCAL_ENV_PATH = Path(__file__).resolve().parents[2] / ".env.local"



def _get_local_env_file() -> Path | None:
    configured_env_file = os.getenv("INVESTMENT_BOARD_ENV_FILE")
    if configured_env_file is not None:
        return Path(configured_env_file)
    if "pytest" in sys.modules:
        return None
    return DEFAULT_LOCAL_ENV_PATH



def _read_local_env_file() -> dict[str, str]:
    env_file = _get_local_env_file()
    if env_file is None or not env_file.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"\"", "'"}:
            value = value[1:-1]
        values[key] = value
    return values



def _get_setting(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return value

    local_settings = _read_local_env_file()
    for name in names:
        value = local_settings.get(name)
        if value is not None:
            return value
    return None



def _get_ai_provider() -> str:
    return (_get_setting("AI_PROVIDER") or "anthropic").strip().lower() or "anthropic"



def _get_ai_api_key() -> str | None:
    provider = _get_ai_provider()
    if provider in DASHSCOPE_COMPATIBLE_PROVIDERS:
        return _get_setting("AI_API_KEY", "DASHSCOPE_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY")
    if provider in OPENAI_COMPATIBLE_PROVIDERS:
        return _get_setting("AI_API_KEY", "OPENAI_API_KEY")
    return _get_setting("AI_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY")



def _get_ai_api_url() -> str:
    provider = _get_ai_provider()
    if provider in DASHSCOPE_COMPATIBLE_PROVIDERS:
        return _get_setting("AI_API_URL", "DASHSCOPE_BASE_URL") or DASHSCOPE_ANTHROPIC_BASE_URL
    if provider in OPENAI_COMPATIBLE_PROVIDERS:
        return _get_setting("AI_API_URL", "OPENAI_BASE_URL") or DEFAULT_AI_API_URL
    return _get_setting("AI_API_URL", "ANTHROPIC_BASE_URL") or DEFAULT_AI_API_URL



def _get_ai_model() -> str:
    provider = _get_ai_provider()
    if provider == "kimi":
        return _get_setting("AI_MODEL", "DASHSCOPE_MODEL") or DASHSCOPE_KIMI_MODEL
    if provider == "dashscope_anthropic":
        return _get_setting("AI_MODEL", "DASHSCOPE_MODEL", "ANTHROPIC_MODEL") or DASHSCOPE_KIMI_MODEL
    if provider in OPENAI_COMPATIBLE_PROVIDERS:
        return _get_setting("AI_MODEL", "OPENAI_MODEL") or DEFAULT_AI_MODEL
    return _get_setting("AI_MODEL", "ANTHROPIC_MODEL") or DEFAULT_AI_MODEL



def _get_ai_http_timeout_seconds() -> float:
    if _get_ai_provider() in DASHSCOPE_COMPATIBLE_PROVIDERS:
        default_timeout = DASHSCOPE_AI_HTTP_TIMEOUT_SECONDS
    elif _get_ai_provider() in OPENAI_COMPATIBLE_PROVIDERS:
        default_timeout = OPENAI_COMPATIBLE_AI_HTTP_TIMEOUT_SECONDS
    else:
        default_timeout = DEFAULT_AI_HTTP_TIMEOUT_SECONDS
    return float(_get_setting("AI_HTTP_TIMEOUT_SECONDS") or str(default_timeout))


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: _get_setting("DATABASE_URL") or DEFAULT_DATABASE_URL)
    ai_provider: str = field(default_factory=_get_ai_provider)
    ai_api_key: str | None = field(default_factory=_get_ai_api_key)
    ai_api_url: str = field(default_factory=_get_ai_api_url)
    ai_model: str = field(default_factory=_get_ai_model)
    ai_temperature: float = field(default_factory=lambda: float(_get_setting("AI_TEMPERATURE") or "0.2"))
    ai_max_output_tokens: int = field(default_factory=lambda: int(_get_setting("AI_MAX_OUTPUT_TOKENS") or "1400"))
    ai_http_timeout_seconds: float = field(default_factory=_get_ai_http_timeout_seconds)
    ai_cache_limit: int = field(default_factory=lambda: int(_get_setting("AI_CACHE_LIMIT") or "20"))
