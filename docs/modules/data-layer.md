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
- [x] Improve database read/write efficiency for current storage-backed flows

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

## Next Requested Scope
- improve read-path efficiency for stock-detail, homepage, and watchlist-backed queries
- reduce unnecessary writes and optimize storage-bound persistence flows
- keep schema or API changes minimal unless profiling proves they are required

## Current Status
done

## Recommended Skills
- `superpowers:brainstorming` for model or boundary changes
- `superpowers:writing-plans` for implementation tasks
- `superpowers:systematic-debugging` for persistence or data issues
- `superpowers:requesting-code-review` when module work is complete
- `superpowers:verification-before-completion` before setting status to `done`

## Verification
- `python3 -m pytest "backend/tests/db" -q`
- schema bootstrap verifies `securities`, `watchlist_items`, and `quote_snapshots` creation, index presence, uniqueness rules, and SQLite foreign-key enforcement
- search ordering verifies exact code, exact name, code prefix, and name-contains behavior with active-only filtering and literal wildcard handling
- watchlist repository verifies idempotent add, remove-by-security-id, and empty-list behavior
- latest quote selection verifies deterministic tie-breaking by `snapshot_time` and snapshot `id`, plus missing-quote outer-join behavior
- bootstrap ingestion verifies normalized success paths plus rollback-safe failure paths for unknown security keys, extra keys, and missing required keys

## Review Evidence
- Date: 2026-05-02
- Verification commands:
  - `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests/db/test_watchlist_view_repository.py" "backend/tests/api/test_holdings_api.py" "backend/tests/api/test_watchlist_sync_api.py" "backend/tests/services/test_stock_sync_service.py" "backend/tests/services/test_stock_sync_with_data.py" "backend/tests/services/test_stock_sync_real_sources.py" -q`
  - `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests" -q`
- Result summary:
  - watchlist latest-quote selection now ranks only snapshots for currently watched securities instead of the entire snapshot table
  - holdings list reads no longer perform an extra joined reread per row
  - watchlist sync now prefetches security metadata in one query instead of looking up each security inside the sync loop
  - stock sync persistence now batches repository writes into a single commit path per security and skips unnecessary refresh work on non-committing upserts
  - targeted repository/API/sync tests passed with `21` tests
  - full backend suite passed with `214` tests
- Remaining follow-up items:
  - None

## Open Questions
- None for the current data-layer efficiency scope.

## 2026-09-12 Repair Scope
Fix deletion of holdings referenced by AI history while retaining history and preventing cached advice reuse after SQLite holding ID recycling. Reproduction in isolated DB raised IntegrityError. Detach nullable holding_id and delete atomically; current holding cache reads require matching holding_id. Verify deletion/history/ID reuse/stock-cache paths with regressions, review before done.

### Review evidence2026-09-12
RED4fail/1pass; GREEN19targeted, full218pass/1known live-search environmental failure. Independent spec and code-quality review PASS; reviewer independently ran5lifecycle tests. Atomic detachment preserves history and prevents recycled-ID reuse; rollback verified. No schema or historical-data migration.
