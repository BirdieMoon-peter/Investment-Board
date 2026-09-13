"""Loopback-only configuration administration without secret-bearing validation errors."""
import os
import secrets
from ipaddress import ip_address
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from app.core.ai_settings_store import AISettingsStore, AISettingsStoreError
from app.core.settings import Settings
from app.schemas.ai_settings import AISettingsUpdate, AISettingsView, is_loopback_host
from app.services.ai_connection_test import test_ai_connection
from app.services.investment_advice_types import InvestmentAdviceProviderError

router = APIRouter()
_DEFAULT_ORIGINS = {'http://localhost:5173', 'http://127.0.0.1:5173', 'http://[::1]:5173'}


def _local_origin(value: str) -> str | None:
    try:
        parts = urlsplit(value)
        if (parts.scheme not in {'http', 'https'} or not is_loopback_host(parts.hostname)
                or parts.username is not None or parts.password is not None
                or parts.path not in {'', '/'} or parts.query or parts.fragment
                or '?' in value or '#' in value or '\\' in value
                or any(c.isspace() or ord(c) < 32 for c in value)):
            return None
        port = parts.port or (443 if parts.scheme == 'https' else 80)
        if not 1 <= port <= 65535:
            return None
        host = parts.hostname.lower()
        if ':' in host:
            host = f'[{host}]'
        default_port = 443 if parts.scheme == 'https' else 80
        return f'{parts.scheme}://{host}' + (f':{port}' if port != default_port else '')
    except ValueError:
        return None


def _access_allowed(request: Request) -> bool:
    # The socket peer is authoritative; forwarded headers never grant access.
    try:
        if request.client is None or not ip_address(request.client.host).is_loopback:
            return False
    except ValueError:
        return False
    host = request.headers.get('host', '')
    backend_origin = _local_origin(f'{request.url.scheme}://{host}')
    if backend_origin is None:
        return False
    if request.headers.get('sec-fetch-site', '').lower() == 'cross-site':
        return False
    origin_header = request.headers.get('origin')
    if origin_header is not None:
        origin = _local_origin(origin_header)
        allowed = {_local_origin(item) for item in _DEFAULT_ORIGINS}
        allowed.add(backend_origin)
        for item in os.getenv('INVESTMENT_BOARD_AI_SETTINGS_ORIGINS', '').split(','):
            configured = _local_origin(item.strip())
            if configured is not None:
                allowed.add(configured)
        if origin is None or origin not in allowed:
            return False
    if request.method != 'GET':
        token = request.headers.get('x-ai-settings-token', '')
        if not token.isascii() or not secrets.compare_digest(token, request.app.state.ai_settings_mutation_token):
            return False
    return True


async def protect_ai_settings(request: Request, call_next):
    if request.url.path != '/api/ai/settings' and not request.url.path.startswith('/api/ai/settings/'):
        return await call_next(request)
    if not _access_allowed(request):
        return JSONResponse({'detail': 'AI settings access denied; use the local application and reload settings'}, status_code=403, headers={'Cache-Control': 'no-store'})
    try:
        response = await call_next(request)
    except Exception:
        # Keep request bodies, rejected keys and filesystem/provider details out of errors.
        return JSONResponse({'detail': 'AI settings request failed; reload settings and retry'}, status_code=500, headers={'Cache-Control': 'no-store'})
    response.headers['Cache-Control'] = 'no-store'
    return response


async def _draft(request: Request) -> AISettingsUpdate:
    try:
        body = await request.json()
        return AISettingsUpdate.model_validate(body)
    except (ValueError, TypeError, ValidationError):
        # Never return ValidationError.errors(): it includes the rejected secret input.
        raise HTTPException(422, detail='Invalid AI configuration; check provider, URL, model, numeric limits and key action') from None


@router.get('/settings', response_model=AISettingsView)
def read_settings(request: Request) -> AISettingsView:
    return AISettingsStore().view(Settings(), request.app.state.ai_settings_mutation_token)


@router.put('/settings', response_model=AISettingsView)
async def save_settings(request: Request) -> AISettingsView:
    draft = await _draft(request)
    store = AISettingsStore()
    try:
        settings = await run_in_threadpool(store.save, draft, Settings())
    except AISettingsStoreError as exc:
        raise HTTPException(exc.status_code, detail=str(exc)) from None
    return store._view_from_settings(settings, 'web', request.app.state.ai_settings_mutation_token)


@router.delete('/settings', response_model=AISettingsView)
def reset_settings(request: Request) -> AISettingsView:
    store = AISettingsStore()
    try:
        store.reset()
    except AISettingsStoreError as exc:
        raise HTTPException(exc.status_code, detail=str(exc)) from None
    return store.view(Settings(), request.app.state.ai_settings_mutation_token)


@router.post('/settings/test')
async def test_settings(request: Request) -> dict:
    draft = await _draft(request)
    try:
        settings = await run_in_threadpool(AISettingsStore().prepare, draft, Settings())
        return await run_in_threadpool(test_ai_connection, settings)
    except AISettingsStoreError as exc:
        raise HTTPException(exc.status_code, detail=str(exc)) from None
    except InvestmentAdviceProviderError as exc:
        raise HTTPException(502, detail=str(exc)) from None
