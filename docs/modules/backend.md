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

## Implemented Files
- `backend/app/main.py`
- `backend/app/api/dependencies.py`
- `backend/app/api/watchlist.py`
- `backend/app/api/stocks.py`
- `backend/app/schemas/security.py`
- `backend/app/schemas/watchlist.py`
- `backend/app/schemas/stock_detail.py`
- `backend/app/services/stock_sync.py`
- `backend/app/services/providers/stock_data_providers.py`
- `backend/app/db/models/price_history.py`
- `backend/app/db/models/financial_metrics.py`
- `backend/app/db/models/company_profile.py`
- `backend/app/db/repositories/price_history_repository.py`
- `backend/app/db/repositories/financial_metrics_repository.py`
- `backend/app/db/repositories/company_profile_repository.py`
- `backend/app/db/repositories/watchlist_view_repository.py`
- `backend/tests/api/conftest.py`
- `backend/tests/api/test_search_securities_api.py`
- `backend/tests/api/test_watchlist_mutation_api.py`
- `backend/tests/api/test_watchlist_list_api.py`
- `backend/tests/api/test_stock_detail_api.py`
- `backend/tests/api/test_stock_sync_api.py`
- `backend/tests/api/test_runtime_smoke.py`
- `backend/tests/db/test_watchlist_view_repository.py`
- `backend/tests/services/test_stock_sync_with_data.py`
- `backend/tests/services/test_stock_data_aggregate_providers.py`

## Consumers
- The frontend module calls `/api/watchlist/securities/search`, `POST /api/watchlist/items`, `POST /api/watchlist/items/custom`, `DELETE /api/watchlist/items/{security_id}`, and `GET /api/watchlist/items` for watchlist flows.
- The frontend module calls `GET /api/stocks/{security_id}` for the stock detail page.
- The frontend module calls `POST /api/stocks/{security_id}/sync` to refresh announcements, news, and stock-data detail sections.
- The backend module depends on the completed data-layer repositories and schemas in `backend/app/db/`.

## Current Milestone
Stock data detail and sync contract on top of the watchlist APIs

## Milestone Scope
Implemented in this milestone:
- market-aware watchlist list responses backed by `WatchlistViewRepository` and reflected in runtime smoke coverage
- stock detail API responses that return `security`, `price_context`, `price_history`, `financial_metrics`, `company_profile`, `announcements`, and `news`
- stock sync service wiring for aggregate announcement, news, price history, financial metrics, and company profile providers
- sync response counts/flags for `price_bars_upserted`, `financial_metrics_upserted`, and `company_profile_updated`
- aggregate provider deduplication for price history and financial metrics plus warning collection across stock-data sources

Deferred in this milestone:
- broader portfolio or AI-analysis backend APIs
- additional stock-data sources beyond the current aggregate adapters
- browser-level acceptance, which belongs to the frontend module

## Current Status
done

## Recommended Skills
- `superpowers:brainstorming` for boundary changes
- `superpowers:writing-plans` for implementation breakdown
- `superpowers:systematic-debugging` for API or server issues
- `superpowers:requesting-code-review` when module work is complete
- `superpowers:verification-before-completion` before setting status to `done`

## Verification
- `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/api/test_runtime_smoke.py" "/Users/peter/Desktop/Investment Board/backend/tests/db/test_watchlist_view_repository.py" -q`
- `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests" -q`
- watchlist API/runtime coverage verified the market-aware contract and deterministic latest-quote selection
- stock detail and sync coverage verified the expanded stock-data detail response and sync summary contract
- full backend verification passed after the market-aware watchlist regression tests were updated to the current contract

## Review Evidence
- Date: 2026-03-13
- Verification commands:
  - `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/api/test_runtime_smoke.py" "/Users/peter/Desktop/Investment Board/backend/tests/db/test_watchlist_view_repository.py" -q`
  - `PYTHONPATH="/Users/peter/Desktop/Investment Board/backend" "/Users/peter/Desktop/Investment Board/backend/.venv/bin/python" -m pytest "/Users/peter/Desktop/Investment Board/backend/tests" -q`
- Result summary:
  - focused backend watchlist regression coverage passed with `4` tests
  - full backend suite passed with `157` tests
  - stock-data review found the frontend had not surfaced the expanded sync summary yet; backend contract coverage was already present in `backend/tests/api/test_stock_sync_api.py`
- Remaining follow-up items:
  - None for the current backend stock-data slice.

## Open Questions
- None for the current backend stock-data scope.

## Implementation Notes
- The watchlist row contract now includes `market`, and backend runtime/repository verification has been updated to lock that contract.
- `StockSyncResult` and `StockSyncResponse` now expose `price_bars_upserted`, `financial_metrics_upserted`, and `company_profile_updated` so consumers can report stock-data sync outcomes instead of only announcement/news counts.
- The final company-profile contract intentionally follows the implemented backend schema: `full_name`, `english_name`, `registered_capital`, `establishment_date`, `website`, `main_business`, and `employees`. Earlier plan examples mentioning `listing_date` and `business_scope` were stale and were not part of the shipped backend contract.
- Aggregate stock-data providers deduplicate price history and financial metrics by natural keys before persistence and include market-qualified source warnings for debugging.
