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
