# Frontend Module

## Goal
Define and implement the presentation layer for the project, including UI structure, interaction flow, and frontend-facing integration points.

## Scope
Included:
- page and component structure
- frontend state and interaction flow
- API consumption behavior from the UI side
- frontend-specific verification items

Excluded:
- backend business logic
- persistence implementation
- one-off developer scripts

## Interfaces
- UI components and pages
- frontend-to-backend API contracts consumed by the UI
- user interaction states and visible outputs

## Tasks
- [x] Define frontend scope for the current milestone
- [x] Add holdings client/types for the backend holdings contracts
- [x] Add AI advice client/types for the backend AI contracts
- [x] Extend `StockDetailPage` with holdings management UI
- [x] Extend `StockDetailPage` with AI advice generation and recent-history UI
- [x] Add bilingual strings and styling support for the holdings/advice slice
- [x] Update focused frontend regression coverage for the new flows
- [x] Run focused and full frontend verification
- [x] Polish presentation layout and optimize key interaction flows across the existing frontend screens
- [x] Validate AI advice usability and improve the stock-detail advice workflow

## Implemented Files
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/styles.css`
- `frontend/src/i18n.tsx`
- `frontend/src/api/watchlist.ts`
- `frontend/src/api/stocks.ts`
- `frontend/src/api/holdings.ts`
- `frontend/src/api/investmentAdvice.ts`
- `frontend/src/types/watchlist.ts`
- `frontend/src/types/holdings.ts`
- `frontend/src/types/investmentAdvice.ts`
- `frontend/src/components/SearchBox.tsx`
- `frontend/src/components/WatchlistTable.tsx`
- `frontend/src/components/StatusMessage.tsx`
- `frontend/src/components/StockHeader.tsx`
- `frontend/src/components/QuoteSummary.tsx`
- `frontend/src/components/PriceContextPanel.tsx`
- `frontend/src/components/CandlestickChart.tsx`
- `frontend/src/components/CandlestickChart.test.tsx`
- `frontend/src/components/PriceHistoryChart.tsx`
- `frontend/src/components/PriceHistoryChart.test.tsx`
- `frontend/src/components/FinancialMetricsPanel.tsx`
- `frontend/src/components/CompanyProfilePanel.tsx`
- `frontend/src/components/AnnouncementList.tsx`
- `frontend/src/components/NewsList.tsx`
- `frontend/src/pages/StockDetailPage.tsx`
- `frontend/src/pages/StockDetailPage.test.tsx`
- `frontend/src/test/setup.ts`

## Consumers
- The current UI consumes backend endpoints at `/api/watchlist/securities/search`, `POST /api/watchlist/items`, `POST /api/watchlist/items/custom`, `DELETE /api/watchlist/items/{security_id}`, and `GET /api/watchlist/items` for watchlist flows.
- The stock detail page consumes `GET /api/stocks/{security_id}` and `POST /api/stocks/{security_id}/sync`.
- The holdings UI consumes `GET /api/holdings`, `POST /api/holdings`, `PUT /api/holdings/{holding_id}`, and `DELETE /api/holdings/{holding_id}`.
- The AI advice UI consumes `POST /api/ai/stocks/{security_id}/advice`, `POST /api/ai/holdings/{holding_id}/advice`, and `GET /api/ai/history`.

## Current Milestone
Professional investment workspace redesign (2026-09-13)

Current scope and acceptance are recorded in the dated redesign section below. Earlier milestone notes remain historical evidence.

## Earlier AI Advice Milestone Scope
Implemented in the earlier milestone:
- holdings frontend contracts aligned to the backend holdings schema
- AI advice frontend contracts aligned to the backend structured recommendation schema
- holdings save/update/remove UI on `frontend/src/pages/StockDetailPage.tsx`
- AI advice generation controls for stock and holding scopes on `frontend/src/pages/StockDetailPage.tsx`
- cached advice history display with replay selection on `frontend/src/pages/StockDetailPage.tsx`
- bilingual copy and dashboard styling support for the new holdings/advice panels
- regression fixes in `frontend/src/pages/StockDetailPage.test.tsx` and `frontend/src/App.test.tsx` for detail-page hydration and new API calls

Originally deferred (browser acceptance has since passed; see dated evidence below):
- browser-level manual acceptance for the AI/holdings stock-detail slice
- portfolio-level AI workflows beyond single stock / single holding detail
- autonomous actions or background advice generation

## Next Requested Scope
- Add an AI configuration form to the existing Settings panel, including save, draft connection test and restoration of environment configuration; proposed design: `docs/superpowers/specs/2026-09-13-web-ai-settings-design.md`. Approved on 2026-09-13; implementation follows the reviewed backend contract.
- improve the presentation polish of the homepage and stock-detail experiences
- refine interaction flows and user-feedback states for the most common actions
- validate AI advice usability, clarify cached/live feedback, and improve the stock-detail advice experience
- keep the work frontend-first unless a backend contract gap is confirmed

## Current Status
done

## Recommended Skills
- `superpowers:brainstorming` for scope or structure changes
- `superpowers:writing-plans` for implementation tasks
- `superpowers:systematic-debugging` for UI bugs or integration failures
- `superpowers:requesting-code-review` when module work is complete
- `superpowers:verification-before-completion` before setting status to `done`

## Verification
- `npm test --prefix "frontend" -- --run src/pages/StockDetailPage.test.tsx`
- `npm test --prefix "frontend" -- --run src/App.test.tsx`
- `npm test --prefix "frontend" -- --run`
- `npm run build --prefix "frontend"`

## Review Evidence
- Date: 2026-05-02
- Verification commands:
  - `npm test --prefix "frontend" -- --run`
  - `npm run build --prefix "frontend"`
  - `PYTHONPATH="backend" "backend/.venv/bin/python" -m pytest "backend/tests" -q`
  - browser acceptance against local frontend/backend runtime
- Result summary:
  - unified homepage/detail status feedback now distinguishes info, warning, and error states more clearly
  - homepage watchlist status noise was reduced by collapsing overlapping messages into a single prioritized status surface
  - stock-detail AI actions now separate cached loads from fresh generation, making live-provider validation explicit in the UI
  - stock-detail warning states now surface as warnings instead of generic errors when the operation otherwise succeeded
  - browser acceptance verified the homepage, detail navigation, sync flow, cached AI path, and fresh AI generation path against the configured local provider
  - frontend suite passed with `9` files and `47` tests
  - frontend production build passed
  - backend suite passed with `214` tests while supporting the validated frontend AI flows
- Remaining follow-up items:
  - None

## Open Questions
- None for the current frontend polish and AI-usability scope.

## Implementation Notes
- `StockDetailPage` now loads holdings and AI history when a security detail view enters the ready state, then derives the current holding and selected advice from that hydrated data.
- The holdings panel intentionally keeps v1 position context minimal: quantity, average cost, target horizon, and notes.
- The AI advice panel shows both structured recommendation fields and the long-form analysis required by the product scope, while surfacing cached-vs-fresh state in the UI.
- Focused stock-detail tests now wait for the new mount-time hydration path so React act warnings do not mask real failures.

## 2026-09-12 Functional Audit
Scope: verify all existing frontend flows and repair reproducible defects, without adding product features.
- [x] Reproduce automatic-sync starvation caused by auto-refresh resetting shared timers; test 60s refresh alongside 180s sync, then keep timer scheduling independent from transient request state.
- [x] Reproduce settings loss during StrictMode reload; initialize settings from persisted storage before the save effect, verify saved language/layout survive remount.
- [x] Complete browser coverage and regression checks; record independent review and fresh evidence.

### Frontend repair task: cache and partial hydration
- Reproduce rejected fetch with a populated 30-minute watchlist cache, expiry/malformed cache and denied localStorage access in frontend/src/api/watchlist.test.ts; ensure a successful API response never fails because cache storage failed. Invalidate cache after successful mutations to avoid resurrecting removed items. Implement fallback around actual request failure, retaining fetchWatchlist signature.
- Reproduce valid holdings plus failed history and valid history plus failed holdings in frontend/src/pages/StockDetailPage.test.tsx. Hydrate the two panels independently in StockDetailPage.tsx and show errors only on the failed panel.
- Run failing regressions, apply minimal fix, run targeted and full frontend checks and independent review.

### Repair review evidence (2026-09-12)
- Timer/settings: RED3failed1passed; GREEN4 lifecycle regressions, full51 tests. Independent spec+quality PASS; browser Chinese/mode/density survive reload.
- Cache/panel isolation: RED17failed22passed; GREEN39 targeted, full76 tests and production build. Independent spec+quality PASS; reviewer reran39 tests.
- Browser final sweep and consolidated evidence remain pending.

### Additional browser defects2026-09-12
390px viewport: homepage document width1144 and detail488, grid min-content/span issue confirmed. Negative holding input currently gives generic English failure even in Chinese. Offline cache needs true saved-at indicator. Cached-advice controls must not generate remotely on miss. Task details recorded in full verification plan; implementation pending after backend review.

### Final frontend repair review — 2026-09-12
- All four final repairs implemented; 94 frontend tests and production build pass.
- Independent specification review in progress; full detail responsive and offline-cache browser checks pending.

- Full-data mobile detail browser check found remaining financial-table overflow (390px viewport,771px document). Review reopened for targeted containment fix.

- Final specification review PASS including financial table wrapper. Independent quality review in progress. Browser offline fallback and full-data 320/390px detail containment pass.

- Quality review found initial-history race: slow mount response can overwrite explicitly selected/generated advice. Reopened for deferred-request regression and selection ownership guard.

- P2 history race: six deferred-response regressions failed before repair;38 focused and100 full tests pass with build. Initial success/error/finally cannot overwrite explicit cached/fresh action. Delta review in progress.
- Full-data detail widths320/390/768/1440 verified with no document overflow; offline saved timestamp and online recovery verified.

### Final review and verification — 2026-09-12
- Independent final specification and quality review PASS. Quality reviewer reran38 detail tests, including6 deferred initial-history races.
- Parent final full frontend run100/100 passed (11 files), production build passed (57 modules); logs in docs/verification/release-readiness.md.
- Browser: full-data 320/390/768/1440 details no document overflow; price/financial tables retain internal scrolling. English/Chinese validation, cache hit/miss, offline original cache timestamp and online recovery passed.
- Main settings restored to original English/compact/live/all sections/60s refresh/180s sync.
- Frontend scope done. Real model generation remains an explicitly tracked backend external-auth blocker; cached fixtures are synthetic.

## Web AI Configuration — 2026-09-13
- Backend contract independently reviewed; frontend implementation complete under `docs/superpowers/plans/2026-09-13-web-ai-settings.md`.
- [x] Add isolated bilingual settings form/client/types with explicit credential actions and draft connection test.
- [x] Verify save/reset/loading/failure/stale-response states in automated tests; responsive browser acceptance follows.
- [x] Complete independent specification and quality review plus isolated browser acceptance.

### Web settings implementation verification
- Implementer:58 focused/158 complete frontend tests passed; production build passed. RED tests preceded implementation, Kimi protocol correction and dirty/success-copy refinement.
- Form is in independent specification review while parent performs isolated browser acceptance.

- Specification review found WHATWG/httpx destination-normalization drift for literal/encoded dot paths. Repair removes duplicate client endpoint identity enforcement: the form gives an advisory on edits, while protected backend409 remains authoritative before any provider call. Corrupt-configuration key decisions remain enforced in the form. Add regressions for both equivalent and conflicting paths.

### Final web settings specification and runtime verification
- Independent specification review PASS after the endpoint-equivalence correction; reviewer reran63 focused tests.
- Parent full frontend suite163/163 passed (14 files), production build passed (59 modules).
- Isolated browser acceptance18/18 passed, including actual HTTP save/test/reset, both protocols, credential transitions, reload, language switching and storage inspection.
- Desktop/mobile screenshots inspected;320/390/768/1440 viewport widths have no document overflow. Independent quality review is active.

### Web AI settings final review — 2026-09-13
- Independent specification and quality review PASS; each reviewer reran 63 focused tests. No unresolved frontend findings remain.
- Parent fresh verification: 163 frontend tests and production build passed; 18 isolated browser checks passed. Actual desktop/mobile captures were visually inspected.
- Original environment and web configuration file hashes, all five watchlist rows and zero holdings match the pre-test baseline. Temporary acceptance services are stopped; the user app remains running.
- Feature evidence: [Web AI settings verification](../verification/web-ai-settings.md). Frontend scope is done; authenticated external analysis remains a separate backend follow-up.

- Repository delivery: feature commit `d1ee72c` is on main; hosted CI run34749705234 passed both jobs. Existing main-app settings API and frontend proxy are ready without modifying user configuration.

## Professional workspace redesign - 2026-09-13
- Requested: use design-taste-frontend for a professional investment dashboard and improved interaction flow.
- Read-only visual/code audit and proposed design complete: `docs/superpowers/specs/2026-09-13-professional-workspace-redesign-design.md`.
- Proposed scope: official Fluent components, light/dark themes, watchlist-first layout, sorting/filtering, detail task groups, settings drawer and draft protection, consistent charts and responsive controls.
- User approved the design on2026-09-13. Implementation follows `docs/superpowers/plans/2026-09-13-professional-workspace-redesign.md`. Previous functionality and review evidence above remain the baseline.

### Theme foundation review
- Official Fluent themes, guarded separate system/light/dark preference and local IBM Plex fonts implemented. Theme RED8 failures preceded14 focused passes; full frontend177 passes and production build passed.
- Independent specification and quality review PASS; both reviewers reran14 theme tests. Actual Edge light/dark pages inspected with no page errors. Homepage/settings is the next increment.
- Supporting dependency maintenance passed clean npm ci and audit0 vulnerabilities (Vite7.3.6/Vitest4.1.11).

### Homepage/search/settings increment in progress
- Watchlist-first layout, controlled filters/sorts, separate search and guarded settings drawer implemented; existing request ownership retained in App.
- Root actual browser found nested-modal focus restoration after Continue editing and a320px theme-selector style collision. Corrections are being verified before independent reviews. First viewport5 rows and390px no-overflow already observed; final matrix uses frozen source.

### Homepage/search/settings final review
-193 frontend tests and production build passed. Independent specification and quality review PASS after the filtered-out spotlight focus repair; reviewers reran10 App and31 focused tests respectively.
- Root actual Edge acceptance:6 drawer guard checks,6 watchlist flow checks,5 sync/cache/error/empty checks. All8 theme-width homepage cases pass without overflow, with64px header; settings also fit four widths.
- Frontend is briefly paused for the requested DeepSeek compatibility increment. Detail groups/chart themes/loading optimization remain Task3 and frontend is not yet done.

- Task2b backend compatibility increment passed both reviews and actual synthetic-only provider acceptance. Frontend Task3 now resumes: detail groups, themed charts and loading optimization.

### Detail workspace entering review
- Three mounted research groups, shared mobile selector, themed charts, accessible wide tables and preserved holding/advice state implemented.
- Fresh verification: 202 frontend tests across 18 files and production build passed. Initial JavaScript is approximately 669.55 kB versus 913.7 kB before lazy loading; warnings remain enabled.
- Pending/rejected lazy imports retain cancel/back actions and a reload recovery path. Local favicon resolves the observed missing resource.
- Root preliminary browser evidence: 11 detail workflows, 3 independent failure/empty/recovery cases, and 24 theme/width/group layouts passed. Final production verification and independent reviews are active.

### Detail specification review correction
- The initial specification review found a lazy-settings fallback focus/Escape gap. Pending/error states now use the official modal drawer shell.
- Independent specification delta review PASS with16 focused tests; root actual browser7 pending/error/transition checks PASS, including Close/Escape/backdrop restoration.
- Fresh final suite203 tests across19 files and production build PASS. Initial static JavaScript681,522 bytes; quality review is active.

### Detail quality review passed; final loading-layout follow-up
- Independent quality review PASS with77 tests across8 focused files plus build. No actionable Task3 code findings remain.
- Final Lighthouse exposed a large initial layout shift (desktop0.293/mobile0.452), principally the workspace columns moving when loading completes. Task4 includes a bounded loading-placeholder/layout correction and regression/browser recheck before completion.


### Final loading stability review
- Structural placeholders now match the market strip, watchlist, spotlight and macro fields; deferred AI labels do not duplicate the loading table. Business request ownership is unchanged.
- Controlled desktop/mobile loading CLS is approximately0.0012/0.0010. Production Lighthouse desktop100/96/100 and mobile92/96/100, with CLS below0.002 in both runs.
- Final independent specification/quality delta reviews and publication are in progress. Full evidence is in `docs/verification/professional-workspace-redesign.md`.


### Final redesign gate passed — 2026-09-13
- Final suite204/204 across20 files and production build passed. Task4 specification and quality reviews independently passed, each rerunning23 tests across4 files and inspecting the README/screenshots.
- Actual desktop/mobile responsive, interaction and loading checks passed; details and limitations are in the consolidated verification document. No actionable review findings remain.
- Environment, authorized web configuration and user watchlist/holdings are preserved. Only the four owned QA services were stopped; main8000/5173 remain available.
- Frontend module is done. Repository publication and hosted CI are tracked in `memory/progress.md`.
