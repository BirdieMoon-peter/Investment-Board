# Data-Layer Module

## Goal
Define and implement the project data model, storage access patterns, and data exchange boundaries used by the application.

## Scope
Included:
- schema or data structure decisions
- repository or query boundaries
- data read and write flow
- data validation at persistence boundaries

Excluded:
- frontend presentation logic
- backend routing concerns beyond data contracts
- unrelated automation scripts

## Interfaces
- data models or schema definitions
- repository/query interfaces
- contracts consumed by backend or scripts

## Tasks
- [x] Define the data entities required for the current milestone
- [x] Define storage and query responsibilities
- [x] Document consumers of the data-layer interfaces
- [x] Define verification steps for reads, writes, and failure cases

## Current Milestone
Stock detail v1 data foundation

## Implemented Files
- `backend/app/core/settings.py`
- `backend/app/db/session.py`
- `backend/app/db/models/security.py`
- `backend/app/db/models/watchlist_item.py`
- `backend/app/db/models/quote_snapshot.py`
- `backend/app/db/models/timestamps.py`
- `backend/app/db/repositories/security_repository.py`
- `backend/app/db/repositories/watchlist_repository.py`
- `backend/app/db/repositories/watchlist_view_repository.py`
- `backend/app/db/services/bootstrap_data.py`
- `backend/tests/db/test_settings_and_session.py`
- `backend/tests/db/test_security_repository.py`
- `backend/tests/db/test_watchlist_repository.py`
- `backend/tests/db/test_watchlist_view_repository.py`
- `backend/tests/db/test_bootstrap_data.py`

## Consumers
- The future backend module will consume `SecurityRepository` for watchlist search and security lookup.
- The future backend module will consume `WatchlistRepository` for add/remove watchlist mutations.
- The future backend module will consume `WatchlistViewRepository` for the watchlist list view with latest quote data.
- Setup/bootstrap flows can consume `bootstrap_market_data()` for normalized security and quote ingestion.

## Milestone Scope
Included for this milestone:
- `securities` as the master data entity for A-share search
- `watchlist_items` as the single-user persisted watchlist relation
- `quote_snapshots` as the minimal latest-price snapshot source for the watchlist view
- uniqueness and query rules needed by watchlist search and list aggregation
- data contracts consumed by the backend watchlist APIs

Excluded for this milestone:
- positions, transactions, recommendations, AI outputs, and news entities
- full K-line or minute-bar storage
- multi-user modeling
- script automation unless required for initial seed/setup

## Current Status
doing

## Recommended Skills
- `superpowers:brainstorming` for model or boundary changes
- `superpowers:writing-plans` for implementation tasks
- `superpowers:systematic-debugging` for persistence or data issues
- `superpowers:requesting-code-review` when module work is complete
- `superpowers:verification-before-completion` before setting status to `done`

## Verification
- `python3 -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db" -q`
- schema bootstrap verifies `securities`, `watchlist_items`, and `quote_snapshots` creation, index presence, uniqueness rules, and SQLite foreign-key enforcement
- search ordering verifies exact code, exact name, code prefix, and name-contains behavior with active-only filtering and literal wildcard handling
- watchlist repository verifies idempotent add, remove-by-security-id, and empty-list behavior
- latest quote selection verifies deterministic tie-breaking by `snapshot_time` and snapshot `id`, plus missing-quote outer-join behavior
- bootstrap ingestion verifies normalized success paths plus rollback-safe failure paths for unknown security keys, extra keys, and missing required keys

## Review Evidence
- Date: 2026-03-10
- Verification commands:
  - `python3 -m pytest "/Users/peter/Desktop/Investment Board/backend/tests/db" -q`
- Result summary:
  - `16 passed in 0.10s`
  - Data-layer foundations for watchlist MVP are implemented and verified for schema creation, repository behavior, latest quote aggregation, and normalized bootstrap ingestion.
- Remaining follow-up items:
  - Backend module still needs API endpoints for search, watchlist add/remove, and watchlist list responses.

## Open Questions
- What storage solution will this project use?
- What are the first entities or datasets needed?
