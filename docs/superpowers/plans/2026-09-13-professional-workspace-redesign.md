# Professional Investment Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Review specification then quality before proceeding to the next implementation task.

**Goal:** Ship the approved professional frontend redesign with a watchlist-first workspace, task-grouped detail view, protected settings drawer and consistent light/dark themes.

**Architecture:** Keep React/Vite and all backend contracts. Fluent UI is the single visual component system, TanStack Table supplies headless table logic, and existing data/advice ownership stays in App and StockDetailPage. Theme and small presentation components isolate design changes from business requests.

**Tech Stack:** React19, TypeScript, Fluent UI React v9, TanStack Table, Phosphor, self-hosted IBM Plex Sans/Mono, Lightweight Charts, Vitest and Playwright.

Approved spec: `docs/superpowers/specs/2026-09-13-professional-workspace-redesign-design.md`. Approval received2026-09-13. Continue in the user's relocated checkout, create a codex feature branch in place, and use isolated data/ports/browser profiles for runtime acceptance. No repeat approval is needed for implementation or previously authorized repository publication.

## Task 1: Theme and visual foundations

Files: package.json/package-lock.json; new `frontend/src/theme.tsx`, `frontend/src/theme.test.tsx`; modify `frontend/src/App.tsx`, `frontend/src/styles.css`, `frontend/src/main.tsx` and test setup as required.

- [x] Verify dependency peer compatibility, install the approved official packages, and capture the unchanged163-test baseline.
- [x] Add failing theme tests for legacy/no preference -> system, explicit light/dark persistence, system change events, unmount cleanup, and denied/malformed storage. Keep theme separate from existing homepage settings to avoid changing their stable fields.

```tsx
export type ThemePreference = 'system' | 'light' | 'dark'
export type ResolvedTheme = 'light' | 'dark'
export interface AppThemeValue {
  preference: ThemePreference
  resolvedTheme: ResolvedTheme
  setPreference: (value: ThemePreference) => void
}
// Contract: export AppThemeProvider, useAppTheme; hook has a safe system/light
// default for existing standalone component tests. Store preference only.
```

- [x] Run the new test file and observe failing behavior before implementation.
- [x] Implement a FluentProvider at the app root using webLightTheme/webDarkTheme, brand blue and IBM Plex typography. Export the hook for charts and settings. Subscribe with matchMedia change events, guarded storage and complete cleanup. Update document data-theme/color-scheme, not business settings or AI state.
- [x] Bundle fontsource font assets with font-display swap; use font weights400/500/600 and Mono400/500 only. No external font requests.
- [x] Replace global gradients/glows/oversized corners with semantic CSS variables that follow the resolved theme. Document layer scale, small-radius controls,8px surfaces and a4px spacing grid. Preserve compatibility classes for pages until the following tasks replace layout. Native charts are adapted in Task3.
- [x] All native controls remaining during migration use coherent focus/contrast; avoid global styles that override Fluent component internals. No marketing imagery, no motion dependency or infinite effects.
- [x] Run focused theme tests, full frontend tests and build. Independently review spec then quality; fix findings and commit only this task's code.

## Task 2: Homepage, search and settings workspace

Files: modify App.tsx, styles.css, i18n.tsx, WatchlistTable.tsx/tests, SearchBox.tsx/tests, AiSettingsPanel.tsx/tests, App tests. Create `components/WorkspaceHeader.tsx`, `components/MarketStrip.tsx`, `components/WatchlistWorkspace.tsx`, `components/SecuritySearchDialog.tsx`, `components/SettingsDrawer.tsx` and associated interaction tests. Split supplementary homepage presentation components when needed to keep App focused on request ownership.

- [x] Add failing interaction tests for numeric sorting including missing values last in both directions; keyword/market filtering; displayed/total counts; exact-object remove confirm/cancel; return-to-list state and focus; separate full-market search; latest search response ownership and duplicate feedback.
- [x] Use TanStack Table on the existing WatchlistItem type. Table state is controlled from App so conditional detail rendering cannot reset filters/sort. Keep default order stable and sorting numeric, never lexicographic price strings.

```tsx
import type { SortingState } from '@tanstack/react-table'
export interface WatchlistViewState {
  query: string
  market: 'all' | 'SH' | 'SZ'
  sorting: SortingState
}
// WatchlistWorkspace receives items, adviceLabels, showAiTags, state/onStateChange,
// onOpenDetail and existing onRemove; no new backend calls from sorting/filtering.
```

- [x] Replace the large homepage hero and grid with a64px header, compact MarketStrip, optional summary and72/28 main/aside layout. Map showHero to compact summary; preserve all presentation/automation/language preferences. Self-hosted mono data, existing source timestamps and actual values only. On1440x900, watchlist header+5fixture rows fit in first viewport.
- [x] Use Fluent Table/Button/Menu/Dialog/Input/Select/Field as applicable. Name is the detail action; menu removal requires explicit object-specific confirmation. Keep callbacks from bubbling into navigation. Small screens show name/code,price,change/actions and expose extra columns via a disclosure.
- [x] Keep homepage request/auto-refresh/auto-sync effects unchanged. Reopening list restores window scroll and selected-security button focus after render, without a new data fetch caused solely by local sorting.
- [x] Move SearchBox to the search dialog, preserve current remote search/custom-code APIs and form names/order. Make onAdd/onAddCustom completion awaitable; keep errors/results in the dialog. Already tracked results have disabled added state. On query changes/unmount discard stale results; Enter submits explicitly and empty query sends no request.
- [x] Guard existing homepage preference reads/writes when localStorage is denied, retaining defaults/session values; a storage failure must not crash App or erase valid saved preferences. Include a full-App regression, not only a theme-provider test.
- [x] Create SettingsDrawer accessible from home/detail via header. Two related groups: interface/refresh and AI configuration. Use official OverlayDrawer/DrawerBody/TabList; preserve current preference labels/order and append theme selection.
- [x] Extend AiSettingsPanel with narrowly scoped callbacks for dirty/busy state and a render prop or optional footer mechanism only if needed. Do not lift keys to App or storage.

```tsx
interface AiSettingsPanelProps {
  onStateChange?: (state: { dirty: boolean; busy: boolean }) => void
}
// Report from an effect with stable parent callback. Saving/testing/resetting
// all disable drawer dismissal. Loaded-only state is not dirty.
```

- [x] AI configuration mounts only when first visited, remains mounted during group switches and unmounts on confirmed drawer close. Every dismissal route uses the same guard: busy -> stay; dirty -> continue-edit/discard confirmation; clean -> close. Discard clears component memory by unmounting; restore/save/test contracts remain unchanged.
- [x] Use existing endpoints only. Status/error copy stays bilingual and controlled. Replace em/en-dash placeholders in visible frontend text with localized missing-value text. Retain legal/disclaimer wording.
- [x] Update regression tests to deliberately open moved dialogs/tabs, never weaken business assertions. Run focused/full tests and build, spec review then quality review, fix and commit.

## Task 2b: Requested DeepSeek compatibility follow-up

User steering2026-09-13 explicitly selects DeepSeek official Flash. Official current model is `deepseek-flash`, endpoint `https://api.deepseek.com`. Protected local settings save and fixed-message test already passed. This is a narrow confirmed provider-contract gap discovered while accepting that request, not a new analysis feature.

- [x] After Task2 is reviewed, pause frontend implementation and activate the backend module for this increment only.
- [x] Preserve existing response fields and strict parser. Clarify the shared system prompt: name all five list fields explicitly; required lists must be nonempty and may state missing/not-applicable context without inventing facts, while warnings may be empty. No coercion, silent retries, extra protocol options or API schema changes.
- [x] Add focused failing provider request-contract coverage for both protocols proving the prompt explicitly distinguishes all list fields from scalar fields and communicates nonempty/missing-context rules. Implement the minimal clarification, then run provider/full backend regressions.
- [x] Update the optional `.env.example` to DeepSeek Flash with an empty key and4096 output budget. Keep runtime defaults for other providers unchanged.
- [x] The actual user web override now uses4096 tokens. Credentials remain in the ignored local configuration only. No user watchlist or holdings may be transmitted during acceptance.
- [x] Repeat actual fresh stock/holding generation, cache reuse and persisted-history checks using only the separate invented-company/invented-position database; remove temporary monkeypatch so final acceptance exercises product code.
- [x] Independent specification then quality review; update backend state only after fresh verification. Commit this bounded increment, then resume frontend Task3.

Diagnostic evidence: original prompt twice produced `position_notes` as a string. Explicit list-field names corrected its type; the original1400-token cap then returned finish_reason=length. With the clarified prompt and4096-token cap,7 actual route/persistence checks passed,2 provider calls (stock9.09s,holding10.81s), and cache reads made no provider calls. These diagnostic changes existed only in the temporary harness. The subsequent product fix and final unpatched acceptance passed; see the verification document.

## Task 3: Detail workspace and themed charts

Files: App.tsx and vite.config.ts if needed for measured loading optimization; StockDetailPage.tsx/tests, StockHeader.tsx, QuoteSummary.tsx, PriceHistoryChart.tsx/tests, CandlestickChart.tsx/tests, PriceContextPanel.tsx, FinancialMetricsPanel.tsx, CompanyProfilePanel.tsx, AnnouncementList.tsx, NewsList.tsx, styles.css/i18n.tsx. Create `components/DetailWorkspaceTabs.tsx` and extracted holding/advice presentation components if needed; keep state and requests in StockDetailPage.

- [x] Add failing tests: default market tab; switching tabs preserves holding draft/selected advice and causes no AI generation; unavailable panels fail independently; mobile selector shares active state; price data disclosure keeps pagination; charts change theme without recreation/range loss.
- [x] Implement three official tabs: market/fundamentals, news/announcements, holdings/AI. On mobile use an identically controlled labeled Select. Keep all tab content mounted but hidden using semantic tabpanels so existing drafts/charts persist. Hidden controls must not be focusable. ResizeObserver redraws a shown chart at nonzero width.
- [x] Top detail header stays compact with back/identity/latest price/change/time and actual sync action. Retain source precision and sign. Render main chart wide, quote summary alongside, fundamentals/profile below; news/announcements remain linked and dated. Holdings and AI retain existing target scope, history/cache/fresh generation behavior.
- [x] Replace form buttons/selects/inputs with Fluent controls without changing field names/order and business handlers. Keep parent ownership/version guards for advice hydration.
- [x] Theme chart using separate effect, preserving mount/data effect dependencies:

```tsx
const { resolvedTheme } = useAppTheme()
useEffect(() => {
  chartRef.current?.applyOptions({
    layout: { background: { type: ColorType.Solid, color: chartPalette.background }, textColor: chartPalette.text },
    grid: { vertLines: { color: chartPalette.grid }, horzLines: { color: chartPalette.grid } },
    timeScale: { borderColor: chartPalette.border },
    rightPriceScale: { borderColor: chartPalette.border },
  })
}, [resolvedTheme])
// The theme effect must not call fitContent, setData or createChart.
```

- [x] Keep existing green-up/red-down semantics consistent across charts/table; numerical missing values use localized text. Price history raw rows are expandable and preserve pagination.
- [x] Reduce the measured913.7kB main bundle by lazy-loading detail/settings with accessible Suspense feedback; preserve request ownership and all dialog state guards. Use chunk grouping only if needed after measuring; do not suppress the size warning. Add a local favicon and index.html link to resolve the measured404 without changing the existing wordmark or inventing a new logo.
- [x] Check charts/tables at320/390/768/1440; no document overflow. Run new and existing detail/chart tests, full frontend suite and build. Independent spec and quality reviews, fixes and commit.

## Task 4: Acceptance, design review and publication

Files: docs/verification/professional-workspace-redesign.md, README.md, docs/images/*, module/registry/roadmap/progress. Bounded frontend loading-layout repairs are included when final Lighthouse/browser evidence identifies a defect. Private runtime artifacts under ignored artifacts/professional-redesign/.

- [x] Record original environment/web settings hashes and read-only watchlist/holdings snapshots. Start only isolated demo backend/database/configuration, frontend proxy and local mock provider. Do not change real user data or send real context to AI.
- [x] Run actual browser feature matrix: search/add/duplicate/remove-cancel/remove, filters/sorts/back restoration, sync/read failure, data groups, pagination, holdings CRUD and state retention, mock AI/cache/history, theme persistence, dirty-close/busy-close/all dismissal routes, settings save/test/clear/reset.
- [x] Inspect both themes at320/390/768/1440; check button labels, contrast, focus order, no page overflow,5-row first viewport, error/loading/empty states, numeric accuracy. Copy self-audit and contextual taste pre-flight; mark marketing-specific rules N/A.
- [x] Run Lighthouse on an isolated production preview with stable demo fixtures. Record performance/accessibility/category results as laboratory evidence and inspect actionable findings, not field CWV guarantees.
- [x] Run fresh complete frontend tests/build and related backend/scripts checks; independent final specification and quality review. Verify fixes with focused regressions and rerun full checks only when changes justify it.
- [x] Capture two actual demonstration screenshots (homepage/detail) after visual inspection; refresh existing settings screenshot if now outdated. Update README/provenance and verification docs with accurate feature/information hierarchy, dependency and privacy bounds.
- [x] Confirm private configuration and watchlist/holdings unchanged, clean up only owned temporary services, keep user main app running. Complete module review state.
- [ ] Commit reviewed changes, normally push HEAD to authorized origin main without force, verify exact remote SHA and hosted CI. Record completed publication in docs/progress and leave a clean worktree.

## Review checklist

All approved specification sections map to Tasks1-4. No backend product scope is added. All client state contracts above use existing WatchlistItem and AiSettingsView types. Theme migration stays separate from AI credentials. Design approval is already complete; routine library/version/implementation decisions are autonomous.
