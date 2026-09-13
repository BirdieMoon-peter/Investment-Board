# Web AI Settings Design

Date: 2026-09-13
State: approved by user on 2026-09-13; implementation authorized

## User request

Allow users to change the embedded AI configuration from the web interface.
The existing application is a local, single-user dashboard; configuration applies
to that running backend instance, including other tabs connected to it.

## Recommended approach and alternatives

1. **Web form with a dedicated backend-local configuration file (recommended).**
   Keep credentials out of browser storage, preserve the existing environment
   configuration as a fallback, and apply saved changes on the next AI request.
   This adds a small settings API without a database migration.
2. Edit the existing environment file from the web form. Fewer configuration
   sources, but process environment variables could silently override a web save,
   and editing the file risks altering unrelated database/runtime settings.
3. Keep a configuration per browser in localStorage. Simple persistence, but it
   stores the secret in browser storage and requires resending it for each AI
   operation; this does not fit the current server-side provider architecture.

## User experience

- Add an **AI configuration** section to the existing homepage Settings panel.
  Keep the existing visual style, Chinese/English translations and responsive
  layout. Implement the form in its own component.
- Basic fields: service type, API address, model name and API key.
- Service choices: OpenAI-compatible, Anthropic-compatible, and DashScope/Kimi.
  Preserve existing aliases internally. Models remain free text to support
  custom services; no remote model discovery is required.
- Advanced fields: temperature, maximum output tokens and request timeout.
  Cache/history retention stays outside this form.
- Buttons: **Save configuration**, **Test connection**, **Restore environment
  configuration**. The restore action clearly states that it removes only the
  web override and presents an inline confirmation before applying it.
- Display the active configuration source and whether a key is configured.
  Never fetch the existing key into the form. An empty replacement field means
  keep the current key only when the service type and normalized endpoint are
  unchanged. Include an explicit **Clear key** control.
- Changing service type or endpoint requires a newly supplied key or an explicit
  choice to save with no key. Never carry a stored credential to a different
  service endpoint silently. Changing model alone may retain the key.
- Saving validates and persists the form without making a provider request.
  It succeeds even if the selected remote service is currently unavailable.
  The next manually requested analysis uses the saved configuration; an already
  running request retains the configuration snapshot with which it started.
- Testing uses the current form values without saving them. Show testing,
  success and controlled authentication/network/timeout/error states. Any form
  edit invalidates the previous test result. Reject stale asynchronous results
  and disable conflicting save/test/reset actions while a request is pending.
- Test copy states that it sends a short fixed test message to the chosen model
  service. It never includes watchlist, holdings, financial context or advice
  history. A successful connectivity check is not full investment-analysis
  acceptance evidence.

## Backend configuration and persistence

- Add a small configuration store at `backend/app/core/ai_settings_store.py`,
  request/response schemas at `backend/app/schemas/ai_settings.py` and endpoints
  at `backend/app/api/ai_settings.py`.
- Default storage: `backend/.ai-settings.json`, excluded from version control.
  `INVESTMENT_BOARD_AI_SETTINGS_FILE` permits an isolated path for tests and
  deployments. Automated tests do not read the default user file.
- Store only the AI fields managed by this form. Never rewrite `.env.local`,
  process environment variables, database settings or historical analysis.
- Effective AI values use a complete saved web configuration when present;
  otherwise retain the current environment > local env file > built-in default
  behavior. Unmanaged settings such as database URL and cache limit keep their
  existing precedence. Reset removes the override and reveals the fallback.
- Load the saved document once per request, validate it as a unit, and combine
  it with the existing immutable Settings object when constructing the advice
  service. Avoid separately reading individual fields during an atomic update.
- Write with a same-directory temporary file and atomic replace, with restrictive
  owner-only permissions. A failed write preserves the previous valid file.
  This is local file storage, not an encrypted credential vault; documentation
  must describe it accurately.
- A malformed saved file produces a controlled settings error. The settings page
  must remain usable for replacement or reset, and unrelated dashboard browsing
  must remain available. Never silently route analysis using fallback credentials
  when a saved override exists but cannot be read.

## API contract

| Method and path | Behavior |
| --- | --- |
| `GET /api/ai/settings` | Effective editable values, `source`, `api_key_configured`, recoverable configuration error if present, and local mutation token; no secret |
| `PUT /api/ai/settings` | Validate and atomically save a complete configuration; return the redacted saved view |
| `DELETE /api/ai/settings` | Remove the web override; return the redacted environment/default view |
| `POST /api/ai/settings/test` | Validate draft, perform fixed-message connectivity test, return controlled status and elapsed time; no persistence |

Mutation/test requests contain a custom header carrying a token obtained from
the settings read endpoint. Restrict these local administration endpoints to
loopback clients, require same-origin requests from supported local frontend or
backend origins, and do not enable permissive CORS. This prevents an unrelated
website from changing the destination to which an existing credential is sent.
Supporting an authenticated multi-user/publicly hosted administration console
is outside this local settings change.

The key update contract has explicit `keep`, `replace` and `clear` actions.
Only `replace` carries a non-empty key. Validation errors expose field names
and controlled messages, never rejected secret input or upstream response bodies.
Responses use `Cache-Control: no-store`; logs and frontend storage do not contain
configuration request bodies or keys.

## Provider handling

- Reuse the existing provider selection and controlled error translation.
  Add a small fixed-message connection-check service instead of calling the
  investment-analysis route with real or synthetic investment records.
- Accept an HTTP(S) service root, a `/v1` base, or the complete protocol endpoint.
  Normalize each to exactly one `/v1/messages` or `/v1/chat/completions` suffix;
  retain custom path prefixes such as DashScope's compatible API prefix.
- Reject URLs with credentials, fragments or query strings. Allow loopback HTTP
  for local proxies and HTTPS for remote services; never follow a redirect that
  forwards the configured key to another destination.
- Validate non-empty model, known provider, finite temperature from 0 to 2,
  output tokens from 1 to 131072 and timeout from 1 to 600 seconds. Provider/model
  limitations narrower than these form limits remain controlled provider errors.
- No preset embeds a real key or an account-specific endpoint. Existing fallback
  configurations remain readable. Explicit model/address input is required when
  switching protocol so an Anthropic default is not reused for OpenAI by mistake.

## Module sequence and files

1. Backend: settings schemas/store/API, safe connection test, provider URL
   normalization and request-time effective settings integration. Relevant
   existing files: `backend/app/core/settings.py`,
   `backend/app/api/investment_advice.py`, `backend/app/main.py`, and
   `backend/app/services/providers/anthropic_investment_advice.py`.
2. Review backend contract and deterministic verification before starting frontend.
3. Frontend: add `frontend/src/components/AiSettingsPanel.tsx`,
   `frontend/src/api/aiSettings.ts` and `frontend/src/types/aiSettings.ts`;
   integrate with `frontend/src/App.tsx`, `frontend/src/i18n.tsx` and scoped CSS.
4. Review frontend, perform isolated browser acceptance, then update README and
   configuration examples. Publish the completed verified change to the existing
   repository under the user's continuing repository maintenance request.

Follow the existing rule that only one technical-layer module is `doing` at a
time. No database schema change, new agent workflow, automated generation,
trading action or remote account creation is part of this feature.

## Acceptance checks

- Saving survives backend restart, changes the next provider request, and leaves
  database/environment configuration untouched. Reset correctly restores fallback.
- Cover key keep/replace/clear, endpoint/provider-change credential boundaries,
  redacted reads and errors, invalid input, interrupted writes and malformed files.
- Check access/origin/token rejection, no redirects with credentials, URL forms
  without duplicate `/v1`, and isolated test paths.
- Connection tests exercise both supported protocols using deterministic local
  mock transports, including 401/403/404/429/503, malformed replies and timeouts.
  Assert their request body contains only the fixed test prompt.
- Frontend tests cover loading, editing, save failures, reopen/reload, key actions,
  reset confirmation, stale responses, test-result invalidation and bilingual copy.
- Browser acceptance uses a separate temporary settings file and demo database
  at desktop and mobile widths. Do not replace the user's current provider key
  or transmit personal holdings/watchlist data during acceptance.
- Run relevant focused tests, complete backend/frontend regression suites and
  frontend build. Record independent review and actual results in module docs.
- Existing external-provider authentication remains a separate acceptance item;
  configuration UI completion must not be reported as proof of fresh investment
  analysis availability.

## Review status

Design self-review complete: configuration precedence, secret lifecycle, draft
testing, service-change behavior, module ownership and acceptance boundaries are
specified. User approved implementation on 2026-09-13. Execute the associated implementation
plan with module reviews and isolated runtime verification.
