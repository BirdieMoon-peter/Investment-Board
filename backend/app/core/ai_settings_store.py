"""Atomic local AI override, separate from environment and database settings."""
import json
import os
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from threading import RLock
from urllib.parse import urlsplit, urlunsplit

from pydantic import ValidationError

from app.core.settings import Settings, _get_setting
from app.schemas.ai_settings import AISettingsUpdate, AISettingsView, StoredAISettings
from app.services.providers.anthropic_investment_advice import canonical_provider_destination

DEFAULT_AI_SETTINGS_PATH = Path(__file__).resolve().parents[2] / '.ai-settings.json'
CONFIGURATION_ERROR = 'Saved AI configuration cannot be read; replace it or restore environment configuration'
URL_DISPLAY_ERROR = 'The saved environment API address contains hidden or invalid URL parts; re-enter a clean API address before saving'
_WRITE_LOCK = RLock()
_MANAGED_FIELDS = ('provider', 'api_url', 'model', 'temperature', 'max_output_tokens', 'http_timeout_seconds', 'api_key')
_ENVIRONMENT_NAMES = (
    'AI_PROVIDER', 'AI_API_URL', 'AI_MODEL', 'AI_TEMPERATURE', 'AI_MAX_OUTPUT_TOKENS',
    'AI_HTTP_TIMEOUT_SECONDS', 'AI_API_KEY', 'OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_MODEL',
    'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL', 'ANTHROPIC_MODEL',
    'DASHSCOPE_API_KEY', 'DASHSCOPE_BASE_URL', 'DASHSCOPE_MODEL',
)


class AISettingsStoreError(RuntimeError):
    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


def _settings_path() -> Path | None:
    configured = os.getenv('INVESTMENT_BOARD_AI_SETTINGS_FILE')
    if configured is not None:
        return Path(configured)
    if 'pytest' in sys.modules:
        return None
    return DEFAULT_AI_SETTINGS_PATH


def _apply(values: StoredAISettings, fallback: Settings) -> Settings:
    return replace(fallback, **{f'ai_{name}': getattr(values, name) for name in _MANAGED_FIELDS})


def _redacted_api_url(value: str) -> tuple[str, bool]:
    """Do not echo credentials embedded in legacy environment URLs."""
    try:
        # Reject ambiguous URLs instead of attempting to display a partial parse.
        if '\\' in value or any(c.isspace() or ord(c) < 32 for c in value):
            return '', True
        parts = urlsplit(value)
        if parts.scheme not in {'http', 'https'} or not parts.hostname:
            return '', True
        port = parts.port
        if port is not None and not 1 <= port <= 65535:
            return '', True
        if parts.username is None and parts.password is None and '?' not in value and '#' not in value:
            return value, False
        host = parts.hostname
        if ':' in host:
            host = f'[{host}]'
        netloc = host + (f':{port}' if port is not None else '')
        return urlunsplit((parts.scheme, netloc, parts.path, '', '')), True
    except (TypeError, ValueError):
        return '', True


class AISettingsStore:
    def __init__(self):
        self.path = _settings_path()

    def _read(self) -> StoredAISettings | None:
        if self.path is None:
            return None
        try:
            raw = self.path.read_text(encoding='utf-8')
        except FileNotFoundError:
            return None
        except (OSError, UnicodeError):
            raise AISettingsStoreError(CONFIGURATION_ERROR) from None
        try:
            return StoredAISettings.model_validate(json.loads(raw))
        except (ValueError, TypeError, ValidationError):
            raise AISettingsStoreError(CONFIGURATION_ERROR) from None

    def effective(self, fallback: Settings) -> Settings:
        values = self._read()
        return _apply(values, fallback) if values is not None else fallback

    def view(self, fallback: Settings, token: str) -> AISettingsView:
        error = None
        try:
            values = self._read()
            settings = _apply(values, fallback) if values is not None else fallback
            source = 'web' if values is not None else _fallback_source()
        except AISettingsStoreError:
            settings, source, error = fallback, 'web', CONFIGURATION_ERROR
        return self._view_from_settings(settings, source, token, error)

    @staticmethod
    def _view_from_settings(settings: Settings, source: str, token: str, error: str | None = None) -> AISettingsView:
        fields = {name: getattr(settings, f'ai_{name}') for name in _MANAGED_FIELDS if name != 'api_key'}
        fields['api_url'], url_was_redacted = _redacted_api_url(settings.ai_api_url)
        # A separate key may remain configured when only its URL display is cleaned.
        # A corrupt override still blocks execution and must not claim a usable key.
        key_configured = bool(settings.ai_api_key) if error is None else False
        if url_was_redacted:
            error = f'{error}; {URL_DISPLAY_ERROR}' if error else URL_DISPLAY_ERROR
        return AISettingsView(
            **fields, source=source, api_key_configured=key_configured,
            configuration_error=error, mutation_token=token,
        )

    def prepare(self, draft: AISettingsUpdate, fallback: Settings) -> Settings:
        if draft.key_action == 'keep':
            current = self.effective(fallback)
            try:
                same_destination = canonical_provider_destination(current.ai_provider, current.ai_api_url) == canonical_provider_destination(draft.provider, draft.api_url)
            except (ValueError, TypeError):
                same_destination = False
            if not same_destination:
                raise AISettingsStoreError('Provider or endpoint changed; replace or clear the API key', 409)
            key = current.ai_api_key
            if isinstance(key, str) and not key.strip():
                key = None
        else:
            key = draft.api_key if draft.key_action == 'replace' else None
        try:
            values = StoredAISettings.model_validate({**draft.model_dump(exclude={'key_action', 'api_key'}), 'api_key': key})
        except ValidationError:
            raise AISettingsStoreError('Current API key cannot be kept; replace or clear the API key', 409) from None
        return _apply(values, fallback)

    def save(self, draft: AISettingsUpdate, fallback: Settings) -> Settings:
        with _WRITE_LOCK:
            settings = self.prepare(draft, fallback)
            if self.path is None:
                raise AISettingsStoreError('An isolated AI settings file is required for this test process')
            temporary_path = None
            try:
                fd, temporary_path = tempfile.mkstemp(prefix=f'.{self.path.name}.', dir=self.path.parent)
                with os.fdopen(fd, 'w', encoding='utf-8') as output:
                    os.fchmod(output.fileno(), 0o600)
                    json.dump({name: getattr(settings, f'ai_{name}') for name in _MANAGED_FIELDS}, output, ensure_ascii=False, allow_nan=False)
                    output.write('\n')
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary_path, self.path)
                temporary_path = None
            except (OSError, ValueError):
                raise AISettingsStoreError('AI configuration could not be saved; the previous configuration is unchanged') from None
            finally:
                if temporary_path is not None:
                    try:
                        os.unlink(temporary_path)
                    except OSError:
                        pass
            return settings

    def reset(self) -> None:
        if self.path is None:
            return
        with _WRITE_LOCK:
            try:
                self.path.unlink(missing_ok=True)
            except OSError:
                raise AISettingsStoreError('AI configuration could not be reset; retry after checking local file access') from None


def _fallback_source() -> str:
    return 'environment' if any(_get_setting(name) is not None for name in _ENVIRONMENT_NAMES) else 'default'


def load_effective_ai_settings(fallback: Settings) -> Settings:
    return AISettingsStore().effective(fallback)
