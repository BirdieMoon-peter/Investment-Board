"""Validated editable AI values. Secret-bearing inputs stay inside protected routes."""
from ipaddress import ip_address
from typing import Literal
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.providers.anthropic_investment_advice import (
    SUPPORTED_ANTHROPIC_COMPATIBLE_PROVIDERS,
    SUPPORTED_OPENAI_COMPATIBLE_PROVIDERS,
)


def is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    if host.lower() == 'localhost':
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def validate_api_url(value: str) -> str:
    try:
        parts = urlsplit(value)
        if (parts.scheme not in {'http', 'https'} or not parts.hostname
                or parts.username is not None or parts.password is not None
                or '?' in value or '#' in value or '\\' in value
                or any(character.isspace() or ord(character) < 32 for character in value)):
            raise ValueError
        if parts.scheme == 'http' and not is_loopback_host(parts.hostname):
            raise ValueError
        # Accessing the port validates malformed/out-of-range port values.
        if parts.port is not None and not 1 <= parts.port <= 65535:
            raise ValueError
        normalized = str(httpx.URL(value))
    except (ValueError, httpx.InvalidURL):
        raise ValueError('Use HTTPS, or HTTP on loopback, without credentials, query or fragment') from None
    return normalized.rstrip('/')


class AISettingsValues(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)

    provider: str
    api_url: str
    model: str
    temperature: float = Field(ge=0, le=2)
    max_output_tokens: int = Field(ge=1, le=131072)
    http_timeout_seconds: float = Field(ge=1, le=600)

    @field_validator('provider', 'api_url', 'model')
    @classmethod
    def nonempty_trimmed(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('A nonempty value is required')
        return value

    @field_validator('provider')
    @classmethod
    def known_provider(cls, value: str) -> str:
        value = value.lower()
        if value not in SUPPORTED_ANTHROPIC_COMPATIBLE_PROVIDERS | SUPPORTED_OPENAI_COMPATIBLE_PROVIDERS:
            raise ValueError('Select a supported provider')
        return value

    @field_validator('api_url')
    @classmethod
    def valid_url(cls, value: str) -> str:
        return validate_api_url(value)


class AISettingsUpdate(AISettingsValues):
    key_action: Literal['keep', 'replace', 'clear']
    api_key: str | None = Field(default=None, repr=False)

    @model_validator(mode='after')
    def valid_key_action(self):
        if self.key_action == 'replace':
            if not self.api_key or not self.api_key.strip() or any(ord(c) < 32 or ord(c) >= 127 for c in self.api_key):
                raise ValueError('Replacement requires a nonempty valid key')
            self.api_key = self.api_key.strip()
        elif self.api_key is not None:
            raise ValueError('Only replace may include an API key')
        return self


class StoredAISettings(AISettingsValues):
    api_key: str | None = Field(repr=False)

    @field_validator('api_key')
    @classmethod
    def valid_key(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or any(ord(c) < 32 or ord(c) >= 127 for c in value)):
            raise ValueError('Invalid stored key')
        return value


class AISettingsView(BaseModel):
    # Fallback environment values remain readable even if older than the form rules.
    provider: str
    api_url: str
    model: str
    temperature: float
    max_output_tokens: int
    http_timeout_seconds: float
    source: Literal['web', 'environment', 'default']
    api_key_configured: bool
    configuration_error: str | None
    mutation_token: str
