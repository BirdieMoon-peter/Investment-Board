from app.core.settings import (
    DASHSCOPE_ANTHROPIC_BASE_URL,
    DASHSCOPE_AI_HTTP_TIMEOUT_SECONDS,
    DASHSCOPE_KIMI_MODEL,
    DEFAULT_AI_API_URL,
    DEFAULT_AI_MODEL,
    OPENAI_COMPATIBLE_AI_HTTP_TIMEOUT_SECONDS,
    Settings,
)



def test_settings_accepts_anthropic_compatible_env_names_for_anthropic_provider(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "compat-token")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://example.com/anthropic")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-custom")

    settings = Settings(database_url="sqlite://")

    assert settings.ai_api_key == "compat-token"
    assert settings.ai_api_url == "https://example.com/anthropic"
    assert settings.ai_model == "claude-custom"



def test_settings_prefers_dashscope_defaults_for_kimi_provider(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "kimi")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "compat-token")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:15721")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    settings = Settings(database_url="sqlite://")

    assert settings.ai_api_key == "compat-token"
    assert settings.ai_api_url == DASHSCOPE_ANTHROPIC_BASE_URL
    assert settings.ai_model == DASHSCOPE_KIMI_MODEL



def test_settings_prefers_explicit_dashscope_ai_env_names(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "dashscope_anthropic")
    monkeypatch.setenv("AI_API_KEY", "ai-key")
    monkeypatch.setenv("AI_API_URL", "https://example.com/anthropic")
    monkeypatch.setenv("AI_MODEL", "custom-model")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "compat-token")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:15721")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    settings = Settings(database_url="sqlite://")

    assert settings.ai_api_key == "ai-key"
    assert settings.ai_api_url == "https://example.com/anthropic"
    assert settings.ai_model == "custom-model"



def test_settings_uses_longer_default_timeout_for_dashscope_and_kimi(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "kimi")
    monkeypatch.delenv("AI_HTTP_TIMEOUT_SECONDS", raising=False)

    settings = Settings(database_url="sqlite://")

    assert settings.ai_http_timeout_seconds == DASHSCOPE_AI_HTTP_TIMEOUT_SECONDS



def test_settings_uses_longer_default_timeout_for_openai_compatible_provider(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "openai_compatible")
    monkeypatch.delenv("AI_HTTP_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("AI_API_URL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    settings = Settings(database_url="sqlite://")

    assert settings.ai_http_timeout_seconds == OPENAI_COMPATIBLE_AI_HTTP_TIMEOUT_SECONDS



def test_settings_reads_local_env_file_when_runtime_env_is_absent(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "AI_PROVIDER=anthropic\nAI_API_KEY=local-key\nAI_API_URL=http://127.0.0.1:8317\nAI_MODEL=gpt-5.4\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("INVESTMENT_BOARD_ENV_FILE", str(env_file))
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("AI_API_URL", raising=False)
    monkeypatch.delenv("DASHSCOPE_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    monkeypatch.delenv("DASHSCOPE_MODEL", raising=False)
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)

    settings = Settings(database_url="sqlite://")

    assert settings.ai_provider == "anthropic"
    assert settings.ai_api_key == "local-key"
    assert settings.ai_api_url == "http://127.0.0.1:8317"
    assert settings.ai_model == "gpt-5.4"



def test_settings_prefers_runtime_env_over_local_env_file(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "AI_PROVIDER=anthropic\nAI_API_KEY=local-key\nAI_API_URL=http://127.0.0.1:8317\nAI_MODEL=gpt-5.4\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("INVESTMENT_BOARD_ENV_FILE", str(env_file))
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setenv("AI_API_KEY", "runtime-key")
    monkeypatch.setenv("AI_API_URL", "https://example.com/anthropic")
    monkeypatch.setenv("AI_MODEL", "claude-runtime")

    settings = Settings(database_url="sqlite://")

    assert settings.ai_api_key == "runtime-key"
    assert settings.ai_api_url == "https://example.com/anthropic"
    assert settings.ai_model == "claude-runtime"



def test_settings_reads_local_openai_env_without_using_anthropic_fallbacks(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "AI_PROVIDER=openai_compatible\nAI_API_KEY=local-key\nAI_API_URL=http://127.0.0.1:8317\nAI_MODEL=gpt-5.4\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("INVESTMENT_BOARD_ENV_FILE", str(env_file))
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "compat-token")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:15721")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("AI_API_URL", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    settings = Settings(database_url="sqlite://")

    assert settings.ai_provider == "openai_compatible"
    assert settings.ai_api_key == "local-key"
    assert settings.ai_api_url == "http://127.0.0.1:8317"
    assert settings.ai_model == "gpt-5.4"



def test_settings_defaults_remain_unchanged(monkeypatch) -> None:
    monkeypatch.delenv("INVESTMENT_BOARD_ENV_FILE", raising=False)
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("AI_API_URL", raising=False)
    monkeypatch.delenv("DASHSCOPE_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    monkeypatch.delenv("DASHSCOPE_MODEL", raising=False)
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)

    settings = Settings(database_url="sqlite://")

    assert settings.ai_api_key is None
    assert settings.ai_api_url == DEFAULT_AI_API_URL
    assert settings.ai_model == DEFAULT_AI_MODEL
