# Backend Module

## Goal
Define and implement the server-side application layer, including request handling, business logic boundaries, and backend-facing interfaces.

## Scope
Included:
- API and service responsibilities
- server-side flow and validation boundaries
- backend integration with the data layer
- backend verification items

Excluded:
- frontend rendering concerns
- direct UI behavior
- standalone automation scripts unless they are part of backend operations

## Interfaces
- API endpoints or server actions
- service-layer behavior
- backend-to-data-layer contracts

## Tasks
- [x] Define backend responsibilities for the current milestone
- [x] List external and internal interfaces
- [x] Identify dependencies on the data-layer module
- [x] Define verification steps for success and failure paths
- [x] Add minimal holdings CRUD APIs backed by a dedicated holdings repository
- [x] Add AI advice endpoints for stock- and holding-scoped analysis
- [x] Add bounded latest-20 AI advice persistence and history reads
- [x] Wire a real model provider through backend settings
- [x] Make provider selection configuration-driven for Anthropic-compatible transports
- [x] Verify Kimi K2.5 integration through the DashScope Anthropic-compatible endpoint
- [x] Add a local ignored AI env-file fallback for reusable developer configuration
- [ ] Complete current uncached runtime AI stock/holding acceptance with an authenticated provider (deterministic provider/error-handling checks pass)

## Implemented Files
- `backend/app/main.py`
- `backend/app/api/dependencies.py`
- `backend/app/api/watchlist.py`
- `backend/app/api/stocks.py`
- `backend/app/api/holdings.py`
- `backend/app/api/investment_advice.py`
- `backend/app/schemas/security.py`
- `backend/app/schemas/watchlist.py`
- `backend/app/schemas/stock_detail.py`
- `backend/app/schemas/holdings.py`
- `backend/app/schemas/investment_advice.py`
- `backend/app/services/stock_sync.py`
- `backend/app/services/investment_advice.py`
- `backend/app/services/investment_advice_types.py`
- `backend/app/services/providers/__init__.py`
- `backend/app/services/providers/anthropic_investment_advice.py`
- `backend/app/services/providers/stock_data_providers.py`
- `backend/app/db/models/price_history.py`
- `backend/app/db/models/financial_metrics.py`
- `backend/app/db/models/company_profile.py`
- `backend/app/db/models/holding.py`
- `backend/app/db/models/investment_advice_cache.py`
- `backend/app/db/repositories/price_history_repository.py`
- `backend/app/db/repositories/financial_metrics_repository.py`
- `backend/app/db/repositories/company_profile_repository.py`
- `backend/app/db/repositories/holdings_repository.py`
- `backend/app/db/repositories/investment_advice_cache_repository.py`
- `backend/app/db/repositories/watchlist_view_repository.py`
- `backend/tests/api/conftest.py`
- `backend/tests/api/test_search_securities_api.py`
- `backend/tests/api/test_watchlist_mutation_api.py`
- `backend/tests/api/test_watchlist_list_api.py`
- `backend/tests/api/test_stock_detail_api.py`
- `backend/tests/api/test_stock_sync_api.py`
- `backend/tests/api/test_holdings_api.py`
- `backend/tests/api/test_investment_advice_api.py`
- `backend/tests/api/test_runtime_smoke.py`
- `backend/tests/db/test_watchlist_view_repository.py`
- `backend/tests/services/test_stock_sync_with_data.py`
- `backend/tests/services/test_stock_data_aggregate_providers.py`
- `backend/tests/services/test_anthropic_investment_advice.py`

## Consumers
- The frontend module calls `/api/watchlist/securities/search`, `POST /api/watchlist/items`, `POST /api/watchlist/items/custom`, `DELETE /api/watchlist/items/{security_id}`, and `GET /api/watchlist/items` for watchlist flows.
- The frontend module calls `GET /api/stocks/{security_id}` for the stock detail page.
- The frontend module calls `POST /api/stocks/{security_id}/sync` to refresh announcements, news, and stock-data detail sections.
- The frontend module calls `GET /api/holdings`, `POST /api/holdings`, `PUT /api/holdings/{holding_id}`, and `DELETE /api/holdings/{holding_id}` for holdings management.
- The frontend module calls `POST /api/ai/stocks/{security_id}/advice`, `POST /api/ai/holdings/{holding_id}/advice`, and `GET /api/ai/history` for AI advice generation and cached history.
- The backend module depends on the completed data-layer repositories and schemas in `backend/app/db/`.

## Current Milestone
AI investment advice backend slice

## Milestone Scope
Implemented in this milestone:
- minimal holdings CRUD APIs backed by a dedicated holdings repository
- AI advice endpoints for stock- and holding-scoped analysis
- real-model provider wiring through backend settings and an HTTP-based AI provider adapter
- configuration-driven provider selection for Anthropic-compatible transports
- Kimi K2.5 integration through the DashScope Anthropic-compatible endpoint
- bounded persistence of the latest 20 generated analyses for replay/history
- backend tests covering holdings contracts, AI advice contracts, provider selection, cache reuse, and bounded history retention

Deferred in this milestone:
- frontend portfolio-level AI workflows beyond stock-detail scope
- autonomous actions, trade execution, or background AI generation
- broader portfolio optimization beyond single-security or single-holding advice

## Next Requested Scope
- validate end-to-end AI advice availability against the configured runtime provider, not just cached responses
- improve backend/provider behavior only where frontend usability validation exposes reliability or clarity gaps
- keep provider changes compatible with the existing structured advice contracts

## Current Status
blocked

## Recommended Skills
- `superpowers:brainstorming` for boundary changes
- `superpowers:writing-plans` for implementation breakdown
- `superpowers:systematic-debugging` for API or server issues
- `superpowers:requesting-code-review` when module work is complete
- `superpowers:verification-before-completion` before setting status to `done`

## Verification
- `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests/services/test_anthropic_investment_advice.py" "backend/tests/api/test_investment_advice_api.py" "backend/tests/api/test_holdings_api.py" -q`
- `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests" -q`
- `npm test --prefix "frontend" -- --run src/pages/StockDetailPage.test.tsx src/App.test.tsx`
- `npm test --prefix "frontend" -- --run`
- `npm run build --prefix "frontend"`
- local acceptance with runtime env:
  - `AI_PROVIDER=openai_compatible`
  - `AI_API_URL=https://your-provider.example/v1/chat/completions`
  - `AI_MODEL=your-provider-model`
  - `AI_API_KEY=<runtime or local ignored env file>`

## Review Evidence
- Review date: 2026-09-13.
- Backend regression suite: 278 tests passed. Provider failure handling, cache lifecycle, holdings CRUD and source timestamp/precision repairs were independently reviewed.
- Structured provider responses in automated tests are fixtures. The current runtime acceptance of fresh AI stock/holding generation is blocked by external provider authentication; this does not block browsing, sync, holdings or cached history.
- Required follow-up: configure an authorized available provider, verify fresh generation with isolated demo stock/holding context, then verify persistence and cache replay before changing this module to `done`.
- Consolidated verification: `docs/verification/release-readiness.md`.

## Implementation Notes
- AI provider settings come from environment variables or the optional local `backend/.env.local`; tests ignore that local file unless explicitly configured.
- Stock and holding analysis uses a configured provider and persists the most recent 20 entries by default. Cached reads do not trigger new model requests.
- Holdings deletion preserves historical advice without allowing stale holding IDs to reuse current-position cache.
- Public data providers can degrade independently; source timestamps and quote precision must remain traceable.
