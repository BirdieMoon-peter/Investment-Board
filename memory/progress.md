# Current Progress

## Current Focus
real external sources v1 backend provider integration

## Current Task
Implement real external announcement/news source adapters and wire them through the manual single-stock sync path.

## Last Completed
- Implemented real external source adapters for announcements and news using Eastmoney and Sina source integrations.
- Wired aggregate providers, stock sync service, and stock sync API to pass `market` and `code` into real-source adapters while preserving warning-aware partial success.
- Verified the real-source backend suite with `25` passing tests.
- Created `CLAUDE.md`
- Created workflow, roadmap, registry, and review checklist documents
- Created module documents for frontend, backend, data-layer, and scripts
- Approved the watchlist MVP design based on `investment_dashboard_plan.md`
- Set `data-layer` as the first active module
- Created the watchlist data-layer implementation plan
- Completed Task 1 backend workspace and local database session bootstrap
- Completed Task 2 SQLModel schema definition and metadata registration for `securities`, `watchlist_items`, and `quote_snapshots`
- Completed Task 3 security repository with `upsert_many` and MVP `search` coverage
- Completed Task 4 watchlist repository with idempotent add/remove behavior and focused repository tests
- Completed Task 5 watchlist view repository with deterministic latest-quote selection and missing-quote coverage
- Completed Task 6 normalized bootstrap ingestion for securities and quote snapshots
- Ran code review for the data-layer module and resolved the bootstrap `status` alignment issue
- Re-ran the full data-layer test suite with `16` passing tests
- Completed review and verification for `data-layer` and moved the module to `done`
- Completed backend Task 1 FastAPI bootstrap and shared API test client setup
- Completed backend Task 2 search API coverage, schema, and route verification in the Python 3.12 virtualenv
- Completed backend Task 3 watchlist mutation API coverage and endpoint wiring with explicit `404` handling
- Completed backend Task 4 watchlist list API coverage and endpoint wiring with missing-quote behavior
- Re-ran the full backend API test suite with `9` passing tests
- Completed backend review and verification and moved the module to `done`
- Completed frontend Task 1 workspace bootstrap, failing shell test, and minimal watchlist page shell implementation
- Completed frontend Task 2 search API client, search interaction flow, and add-to-watchlist UI wiring
- Completed frontend Task 3 watchlist list rendering, remove interaction, explicit status states, and reload flow
- Applied frontend review fixes for visible add/remove failures, expanded focused frontend state coverage, and refreshed the frontend module document
- Re-ran the full frontend test suite with `3` passing files and `9` passing tests
- Completed frontend review and verification and moved the module to `done`
- Completed integration seed/runtime support, smoke verification, Vite proxy wiring, and local startup scripts
- Verified local backend endpoints respond over HTTP and frontend dev server responds on `127.0.0.1:5173`
- Marked `scripts` integration work as `done`
- Approved the stock detail v1 design for planning
- Completed stock detail v1 Task 1 detail schema models for daily price bars, announcements, and news items with focused schema verification
- Completed stock detail v1 Task 2 repository queries and aggregate detail repository with focused db coverage
- Completed stock detail v1 Task 3 backend stock detail response schemas, GET /api/stocks/{security_id}, and focused API verification
- Completed stock detail v1 Task 4 frontend watchlist-to-detail navigation and stock detail page shell with focused frontend verification
- Completed stock detail v1 Task 5 frontend stock detail API client, populated detail section rendering, and focused detail page verification
- Re-ran stock detail cross-layer verification with `7` backend tests passing and `2` frontend test files / `10` tests passing
- Started information-sync v1 Task 2 and confirmed the focused stock sync API test fails before implementation due to the missing sync endpoint dependency
- Completed information-sync v1 Task 2 sync response schema, POST stock sync API route, and focused API verification with `2` passing tests
- Completed information-sync v1 Task 3 frontend sync trigger, sync messaging, detail refresh, and focused detail page verification with `6` passing tests
- Started real-information-provider-v1 Task 2 warning-aware backend sync work and confirmed focused warning tests fail before implementation
- Completed real-information-provider-v1 Task 2 warning-aware sync service and sync API verification with `6` passing focused backend tests
- Started real-information-provider-v1 Task 3 frontend warning-aware sync display work and confirmed the focused detail page test fails before UI implementation
- Completed real-information-provider-v1 Task 3 warning-aware sync messaging and focused detail page verification with `6` passing tests

## Next Step
The next logical slice is to harden real-source provider behavior for production-like usage (pagination, better payload normalization, and optional provider diagnostics) or move to the next product module such as holdings management.

## Blockers
- Browser-level manual acceptance for the real-source sync flow still depends on the user returning.

## Verification Pending
- Manual acceptance of the real-source stock sync flow in the browser.
