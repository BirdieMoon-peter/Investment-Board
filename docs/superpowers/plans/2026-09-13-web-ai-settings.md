# Web AI Settings Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development to implement this plan task-by-task, with specification and quality review before changing modules.

**Goal:** Let users edit, save, test and restore the AI configuration from the existing web Settings panel.

**Architecture:** A dedicated local JSON store supplies a complete request-time AI override; the existing environment configuration remains the fallback. A redacted settings API and fixed-message connection tester serve a bilingual form. Database settings and personal data are outside the mutation boundary.

**Tech Stack:** FastAPI, Pydantic, httpx, Python dataclasses, React, TypeScript, Vitest and pytest.

Approved design: `docs/superpowers/specs/2026-09-13-web-ai-settings-design.md`.
User approved implementation on 2026-09-13. Continue in the current non-main
project checkout as requested in this task; use isolated paths/ports for runtime
acceptance. Do not change actual credentials during tests.

## Task 1: Backend configuration and connection check

Files:
- Create `backend/app/core/ai_settings_store.py`, `backend/app/schemas/ai_settings.py`, `backend/app/api/ai_settings.py`, `backend/app/services/ai_connection_test.py`.
- Modify `backend/app/api/investment_advice.py`, `backend/app/main.py`, `backend/app/services/providers/anthropic_investment_advice.py`, `.gitignore`.
- Add `backend/tests/api/test_ai_settings_api.py`, `backend/tests/services/test_ai_connection_test.py`, `backend/tests/db/test_ai_settings_store.py`; extend provider URL regression tests.

- [x] Add failing tests using temporary configuration files and deterministic mock HTTP transports. Validate persistence/reload, keep/replace/clear, changed-endpoint rejection, invalid/corrupt file recovery, atomic-write failure, all-redacted responses/errors, access checks, both protocols and connection-error states.
- [x] Implement canonical request fields and explicit key action:

```python
# Input/output field names shared with TypeScript.
provider: str
api_url: str
model: str
temperature: float
max_output_tokens: int
http_timeout_seconds: float
# Write/test input only:
key_action: Literal["keep", "replace", "clear"]
api_key: str | None
# Redacted output only:
source: Literal["web", "environment", "default"]
api_key_configured: bool
configuration_error: str | None
mutation_token: str
```

- [x] Validate request bodies manually within protected settings routes (or sanitize route-specific validation errors) so FastAPI never echoes a submitted key. Errors use `detail` with controlled code/string, optionally field names but no raw input. Return `Cache-Control: no-store` on success and errors.
- [x] Implement `GET/PUT/DELETE /api/ai/settings` and `POST /api/ai/settings/test`. Use loopback client/Host/Origin checks, no permissive CORS, and an in-memory unguessable mutation token issued to the same-origin UI. Trust only actual loopback hostnames/literals; do not accept suffix-lookalikes. Permit the default frontend port 5173 plus the request origin, and an explicit server environment allowlist for alternate local development ports. Do not trust forwarded headers.
- [x] Persist owner-only JSON with atomic replace under `INVESTMENT_BOARD_AI_SETTINGS_FILE` or `backend/.ai-settings.json`; preserve original file on failure and redact corruption errors. Disable default user-file access under pytest. Reset must work when the file is corrupt.
- [x] Build each AI service from one effective Settings snapshot:

```python
settings = load_effective_ai_settings(Settings())
```

Keep `Settings()` itself as the old environment reader, so database and unrelated routes remain unchanged. Catch store errors as controlled AI-unavailable responses at the advice dependency boundary; keep settings recovery functional.

- [x] Normalize service root, `/v1` and complete endpoint URLs exactly once; reject query/fragment/userinfo and non-loopback plaintext HTTP for new writes. Disable redirects. Compare canonical provider protocol and resolved endpoint before permitting stored-key reuse; aliases using the same protocol and endpoint may retain the key.
- [x] Connection tester sends a fixed `Reply with OK.` message using the selected model and a small token budget, independent of all database/advice repositories. Reuse sanitized provider errors, require nonempty text, close the HTTP client. Return `{ "ok": true, "elapsed_ms": number }` on success; use sanitized errors otherwise. Test the draft without saving it.
- [x] Run focused tests, then `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests -q`. Review specification compliance, fix findings, then request independent quality review and fix findings. Record actual evidence in backend module docs. Retain the separate live investment-analysis auth blocker.

## Task 2: Frontend settings form

Files:
- Create `frontend/src/types/aiSettings.ts`, `frontend/src/api/aiSettings.ts`, `frontend/src/components/AiSettingsPanel.tsx`, `frontend/src/components/AiSettingsPanel.test.tsx`, `frontend/src/api/aiSettings.test.ts`.
- Modify `frontend/src/App.tsx`, `frontend/src/i18n.tsx`, `frontend/src/styles.css`; adjust existing integration tests only where the new lazy settings fetch requires it.

- [x] Use the reviewed backend contract, with request header `X-AI-Settings-Token` agreed before implementation. Keep the token and replacement key in component memory only. API calls use `cache: 'no-store'`; no localStorage/sessionStorage persistence of AI values or keys.
- [x] Add focused failing component/client tests for initial read, input edits, successful/failed save, clearing a key, replacement, explicit empty-key save after service change, draft test, restore confirmation, retry, unmount/stale response handling, bilingual rendering and test-result invalidation.
- [x] Mount `<AiSettingsPanel />` below the current homepage settings groups. Load only when opened, render labeled inputs, masked key entry and configured-state text. Keep it independent of auto-refresh/auto-sync settings and avoid adding model API calls to existing effects.
- [x] Implement form state for `loading`, `idle`, `saving`, `testing`, `resetting` with one active operation. Disable the form fieldset during mutation/test. Abort or ignore obsolete asynchronous responses after unmount; edits clear success/test status. Never repopulate a saved key from the server.
- [x] Preserve backend-provided provider aliases in the select. On service change clear model/address rather than silently reusing a different protocol's defaults, and explain replace/clear when destination changes; let the protected backend409 authoritatively enforce destination equivalence before any provider call. Basic inputs are provider/address/model/key; advanced numeric controls use agreed schema limits.
- [x] Buttons save the full draft, test the full draft without persistence, or confirm removal of only the web override. Show current source and actionable Chinese/English errors without displaying raw secret-bearing responses. Recover from malformed stored configuration by allowing replacement/clear or reset.
- [x] Add scoped responsive CSS using the existing dark panel and controls; field widths must fit 320px screens, keyboard focus and status feedback must remain visible.
- [x] Run `npm test --prefix frontend -- --run` and `npm run build --prefix frontend`. Complete independent spec and quality reviews, record evidence in frontend module docs.

## Task 3: Isolated runtime acceptance and repository delivery

Files: `README.md`, `backend/.env.example`, module docs, roadmap, registry, `memory/progress.md`, `docs/verification/web-ai-settings.md`.

- [x] Start an isolated demo backend with its own DB and settings-file path, a local fixed-response mock provider, and a frontend proxy on an unused local port. Test credentials are invented local fixtures.
- [x] Exercise the actual browser: open Settings, edit provider/model/URL/key, save, reopen/reload, test connection, see a controlled auth failure, clear key, restore/cancel restore, and inspect Chinese/English at desktop/mobile sizes.
- [x] Restart only the demo backend and verify saved values remain. Verify no secret appears in GET/error responses or browser localStorage, and live user configuration/database remain unchanged.
- [x] Capture an actual UI screenshot for feature evidence. Check final backend/frontend results and any shared launcher regression required by changes, then stop temporary owned processes while retaining the user's app.
- [x] Update README with web-first setup, configuration precedence, key handling, connection-test meaning and local-only scope. Update `.env.example` as fallback configuration documentation.
- [x] Record review/verification, commit the complete reviewed feature, push normally to the previously authorized repository's `main`, and verify the remote commit plus hosted CI. Do not force push or claim external AI auth has been repaired by this UI.
