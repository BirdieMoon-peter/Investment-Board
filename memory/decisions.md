# Decisions

## 2026-03-10
### Workflow style
- The project will use a Claude Code-specific workflow instead of a tool-agnostic workflow.
- Reason: the user explicitly wants efficient skill usage and memory-backed development flow.

### Project mode
- The workflow is optimized for single-developer use.
- Reason: keep coordination lightweight while preserving review discipline.

### Module strategy
- Modules are defined by technical layer, not by feature.
- Reason: the user wants module completion and review to happen at the technical-layer level.

### Process authority
- Markdown documents are the source of truth for workflow state and module execution.
- Reason: the user wants development docs to lead the entire process.

### Watchlist MVP data-layer foundation
- The first executable application code lives in `backend/`.
- Reason: the watchlist MVP starts with the data-layer module but needs a stable Python workspace that can later host backend APIs without moving persistence code.
- The local MVP uses SQLite persistence through SQLModel; PostgreSQL remains a later migration target.
- Reason: single-user local development is the current target, and SQLite keeps the first module lightweight while preserving a later path to PostgreSQL.
- Bootstrap ingestion accepts normalized records and does not fetch external market data directly.
- Reason: the data-layer module should validate and persist structured input, while external ingestion mechanisms remain a later concern.

### Watchlist MVP backend foundation
- The watchlist MVP backend uses FastAPI with thin route handlers over repository classes.
- Reason: this keeps endpoint logic narrow and pushes data concerns into the completed repository layer.
- Backend watchlist mutations and deletion use `security_id` as the request key.
- Reason: the approved watchlist MVP contracts already use `security_id` as the stable relation key across modules.
- Missing securities and missing watchlist rows return `404` from backend endpoints.
- Reason: these are request-level failures that should be explicit to the frontend rather than silently ignored.

### Watchlist MVP frontend foundation
- The watchlist MVP frontend uses a small local-state React app instead of introducing global state libraries.
- Reason: the MVP only needs one page and a narrow interaction flow, so local component state keeps the frontend simple.
- The frontend renders explicit empty, no-result, error, and missing-quote states.
- Reason: the approved watchlist MVP requires visible UI handling for absent results and incomplete quote data rather than silent blanks.

### Watchlist MVP local runtime
- Local watchlist MVP runtime uses a seeded SQLite database plus uvicorn and Vite dev servers.
- Reason: this is the smallest setup that lets the completed frontend, backend, and data-layer run together for local acceptance.
- Vite proxies `/api` requests to the local FastAPI backend at `http://127.0.0.1:8000` during development.
- Reason: this keeps frontend API calls simple while allowing the backend to run as a separate local process.

### Stock detail v1
- Stock detail v1 uses a single aggregated backend endpoint at `GET /api/stocks/{security_id}`.
- Reason: this keeps the frontend detail page simple and allows partial sections to be returned together from one backend read path.
- Stock detail v1 enters only from the watchlist list; direct code-route entry is deferred.
- Reason: this keeps the next product slice narrow and reuses the completed watchlist flow as the only entry point.

### Information sync v1
- Information sync v1 uses `POST /api/stocks/{security_id}/sync` for manual single-stock sync.
- Reason: this keeps detail reads stable while making sync an explicit user-triggered action.
- Stock detail reads and sync writes remain separate interfaces.
- Reason: this avoids mixing read latency and external-source failure paths into the core detail endpoint.

### Real information provider v1
- Real information provider v1 uses aggregate providers with multiple source adapters per information type.
- Reason: this improves sync success rate while keeping source-specific parsing isolated from the sync service.
- Partial source failures surface as warnings instead of failing the entire sync by default.
- Reason: the sync path should prefer usable incremental data over all-or-nothing behavior when at least one source succeeds.
- Runtime provider fetching uses `httpx` plus lightweight HTML/JSON parsing for external-source adapters.
- Reason: this keeps provider integration small and testable while matching the current Python backend stack.
- Real-source sync passes `market` and `code` through the sync service into aggregate providers.
- Reason: source adapters need exchange-specific identifiers to build upstream requests without adding repository lookups inside the provider layer.

### Real source hardening v1
- Real source adapters retry network/timeout errors once with 1-second delay.
- Reason: improves reliability for transient network issues without excessive delay.
- Error messages include source name, stock code, market, and exception type with row index context.
- Reason: makes debugging production issues much easier by providing precise failure location.
- Adapters support pagination up to 3 pages by default (configurable via max_pages parameter).
- Reason: ensures comprehensive data retrieval while limiting resource usage.
- Diagnostic logging records request statistics (elapsed time, record counts) at INFO level for success and WARNING level for failures.
- Reason: provides observability for production monitoring without requiring external dependencies.

### Frontend i18n provider stability
- The frontend i18n provider memoizes `t` and `formatDateTime` so their identities stay stable unless the language changes.
- Reason: unstable context function identities were retriggering effect dependencies in consumers such as `frontend/src/App.tsx`, which caused duplicate watchlist loads and test flakiness.

### Homepage dashboard overview wiring
- Homepage market indexes and macro data load from a dedicated frontend client for `GET /api/homepage/overview` and remain independent from watchlist loading.
- Reason: homepage overview failures should not block watchlist rendering or core add/remove/detail flows.
- Homepage presentation preferences remain frontend-only in `localStorage`, including density and section visibility toggles.
- Reason: the approved homepage slice explicitly keeps settings lightweight and local instead of adding backend persistence.

### Stock detail holdings and AI hydration
- The stock detail frontend hydrates holdings and AI advice history on ready-state entry and keeps that work independent from the base stock-detail fetch.
- Reason: holdings/advice failures should not block the core stock-detail data from rendering, and the detail tests need a stable mount-time hydration pattern to match browser behavior.

### Anthropic-compatible AI provider selection
- The backend AI module selects supported Anthropic-compatible providers through a small provider factory, with `anthropic`, `dashscope_anthropic`, and `kimi` mapped through the same Messages-style transport adapter.
- Reason: the AI settings already exposed provider/base-url/model configuration, and making selection real avoids misleading dead configuration while keeping DashScope/Kimi integration lightweight.
- Anthropic-compatible base URLs are normalized to the final `/v1/messages` request path, and DashScope/Kimi uses a longer default timeout unless explicitly overridden.
- Reason: the configured DashScope endpoint is a base URL rather than the final messages URL, and live Kimi requests required a longer timeout than the original Anthropic default.

### Local backend AI config fallback
- Backend settings load `backend/.env.local` as a local fallback outside pytest, and runtime env vars still take precedence over file values.
- Reason: the user wants reusable project-local LLM configuration without committing secrets to versioned files or making automated tests depend on developer-local credentials.
- Automated tests ignore the default local env-file path unless `INVESTMENT_BOARD_ENV_FILE` is explicitly set.
- Reason: pytest and CI should stay deterministic even when a developer has local credentials configured.

### Local OpenAI-compatible AI provider support
- The backend AI module also supports an `openai_compatible` provider path that sends OpenAI-style chat completions requests to local proxy endpoints.
- Reason: an OpenAI-compatible model service exposes `/v1/chat/completions`, not Anthropic `/v1/messages`, so fresh AI generation required a protocol-specific adapter.
- OpenAI-compatible settings read `AI_*` or `OPENAI_*` values without falling back to unrelated `ANTHROPIC_*` env vars, and they use a longer default timeout.
- Reason: shell-level Anthropic env vars were incorrectly overriding the local proxy config, and real stock-analysis generations took longer than the original 30-second default.

## 2026-09-13
### Web AI configuration
- The local Settings panel edits a complete request-time AI override; environment values remain the fallback and reset only removes the web override.
- Credentials are stored in an ignored owner-only local file and never returned by settings APIs or persisted in browser storage. This is a single-user loopback feature, not a shared hosted credential service.
- The backend is the sole authority for canonical protocol/endpoint equivalence and retained-key use. The frontend provides edit guidance and controlled conflict recovery.
- Connection tests use the current draft and a fixed short message, without accessing user watchlists, holdings or analysis history. They neither save the draft nor establish full external investment-analysis availability.
