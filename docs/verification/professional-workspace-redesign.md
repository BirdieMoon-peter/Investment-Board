# Professional workspace redesign verification

Date: 2026-09-13
Status: complete. Implementation, independent reviews, local verification and repository publication passed.

## Scope and baseline

The approved [design](../superpowers/specs/2026-09-13-professional-workspace-redesign-design.md)
and [plan](../superpowers/plans/2026-09-13-professional-workspace-redesign.md)
cover the frontend theme, watchlist/settings interactions and grouped stock research.
The original frontend baseline passed 163 tests across 14 files.

The original watchlist heading was below the first viewport at approximately
1137px in a 1440x960 browser while some requests were still loading. Opening
settings inserted approximately 1058px of content above the workspace. Charts
had white canvases in the dark page. The redesign targets these measured issues.

## Acceptance matrix

| Area | Evidence | State |
| --- | --- | --- |
| Theme | 14 theme tests; browser reload, explicit preference and live system change | Passed |
| First viewport | Five demo rows visible at 1440x900; 64px header | Passed |
| Watchlist | Keyword/market filters, numeric sorting, null-last in both directions | Passed |
| Detail return | Filters/sort retained; origin focus including filtered-out spotlight | Passed |
| Search | Explicit submit, add, duplicate feedback, custom code; stale-request regressions | Passed |
| Removal | Object-specific confirmation, cancellation and controlled failure | Passed |
| Research groups | Retained drafts/advice, shared mobile state and zero automatic generation | Passed |
| Chart | Lifecycle regressions; actual canvas retained on theme/group changes, resize and pagination | Passed |
| Holdings and advice | Actual isolated CRUD, two explicit mock calls, cache with no new calls and history selection | Passed |
| Settings | Lazy AI load, retained drafts, all dirty/busy dismissal routes, focus return | Passed |
| AI configuration | Draft auth failure/test/save, protocol/key boundary, clear/reset, bilingual state | Passed |
| Responsive | Homepage both themes at 320/390/768/1440; drawer at all four widths | Passed |
| Accessibility | Home/drawer keyboard trapping and focus return; Axe findings below | Passed; reviewed |
| Lighthouse | Production desktop 100/96/100; mobile 92/96/100; CLS below 0.002 | Passed; lab evidence |
| Regression/review | 204 frontend tests/build; 386 backend tests; 15 launcher tests and standalone smoke | Independent specification and quality passed |
| Delivery | Published README, two main screenshots, About/topics, normal push and exact-commit hosted CI | Passed |

## Isolation and credentials

Acceptance runs in a copy of the previous isolated public demo database, never
the user's database. Public historical detail data for two demo securities is
retained. Three fixed quote fixtures exercise five watchlist rows. Homepage,
search and sync overrides exist only in a temporary acceptance app. A loopback
mock model returns visibly identified demonstration analysis. Logs omit keys.

The real app remains on 8000/5173. Owned acceptance services use 8011/5175/5177/8321.
Scripts, logs, configuration and test databases are outside tracked source files.
Original environment hashes and watchlist/holdings snapshots are saved privately.

The user separately authorized DeepSeek official Flash configuration. The protected
web API saved `deepseek-flash` at `https://api.deepseek.com`, with a 4096-token output
budget. A fixed-message connection test passed in 461.72ms. An updated private hash
baseline records this authorized configuration change. The original environment
file, five watchlist rows and zero holdings remain unchanged. Private settings are
ignored by Git; a value-based scan finds no credential in tracked files or diffs.

## Actual DeepSeek acceptance

Synthetic-only actual requests exposed an ambiguous list-field prompt and truncation
at the old output cap. The shared prompt now names all five array fields explicitly;
the strict response parser and provider contracts are unchanged. Independent
specification and quality reviews passed, as did 41 provider tests and 386 backend
tests. A temporary diagnostic patch was removed before the final acceptance.

Final product code passed seven route/persistence checks: two fresh actual calls
(stock 7.69s, holding 10.65s), cache reuse with no additional provider call, history
and persisted reads through new application/database sessions. Only an invented
company, quote and position were transmitted. This resolves the account's earlier
integration blocker; it verifies functionality, not investment accuracy or future
provider availability.

## Completed frontend increments

Theme foundations use official Fluent v9, TanStack v8, Phosphor and self-hosted
IBM Plex fonts with React 19. Existing toolchain advisories were addressed using
compatible Vite 7.3.6/Vitest 4.1.11 and patched transitive dependencies. A clean
`npm ci` succeeded and `npm audit` reported zero vulnerabilities. Fourteen theme
tests, the 177-test intermediate suite and its build passed both independent reviews.

The watchlist/search/settings increment passed 193 tests, its production build,
and independent specification and quality reviews. Two RED/GREEN regressions
cover returning from a filtered-out spotlight and an origin hidden by settings.
Actual browser evidence includes:

- Six drawer checks: lazy mounting, tab draft retention, Escape/continue,
  discard/unmount/reopen, and close button/Escape/backdrop during a pending test.
- Six watchlist flows: numeric sorting, preserved filter/focus, explicit search,
  duplicate feedback, missing quote order, removal and custom-code fallback.
- Five state checks: manual sync, offline cache, online recovery, failed removal
  and empty watchlist.
- Ten AI settings checks: invented-key failures and success, advanced values,
  protocol/key boundary, clear/reset, Chinese draft retention and secret storage.
- Four keyboard/theme checks: preference persistence, system changes, search
  focus trapping/restoration and drawer focus trapping/restoration.

## Accessibility and performance notes

Axe identifies Fluent/Tabster's own `data-tabster-dummy` focus sentinels under
`aria-hidden-focus`. Raw findings are retained and app-owned elements remain subject
to the same rule. The pattern is tracked in
[Fluent issue 27517](https://github.com/microsoft/fluentui/issues/27517). No sentinel
or audit rule is removed to inflate the score. Manual keyboard trapping and origin
restoration pass. A real nested-dialog restoration defect was fixed and retested.

Immediate theme-change captures initially caught Fluent's short color transition.
Final screenshots wait for active transitions to finish; fresh dark loads render
correct foreground colors.

The initial production desktop Lighthouse result was Performance 100,
Accessibility 96, Best Practices 96: FCP 645ms, LCP 689ms, TBT 0ms, CLS 0.0156.
A missing favicon caused a console error and the main bundle measured 913.7kB.
Task 3 addresses these findings. All reported Lighthouse results are local lab
measurements with fixed fixtures, not field Core Web Vitals guarantees.

## Applicable design pre-flight

The requested taste skill explicitly excludes dashboards; the approved design
uses official Fluent product components. Applicable checks are hierarchy, source
precision, theme/color/shape consistency, typography, contrast, copy, interaction
states, keyboard navigation and mobile layouts. Marketing hero, photography,
bento, brand walls, scroll narratives and testimonial rules are N/A. Published
images are actual browser captures, with no generated or composited interface.

## Final production browser pass

- Eleven detail workflows passed against the production preview, including
  raw-price page retention, source links, unsaved holding drafts, mobile/desktop
  state, holding create/update/delete, two explicit mock analyses and cache/history.
- Three independent error/empty/recovery cases passed; available market/news
  content remains usable when holdings or history fails.
- Eight homepage and 24 detail group/theme/width cases passed without page
  overflow. Settings fit four widths. Wide-table keyboard findings were fixed;
  repeated Axe checks now identify only the documented library sentinels.
- Final production settings checks passed: six guard cases, ten AI configuration
  flows and four keyboard/theme cases.
- Independent specification review identified missing focus restoration/Escape
  behavior only in the newly introduced lazy settings loading/error fallback.
  The official drawer shell correction passed independent specification review
  and seven actual stalled/failed/transition browser checks before publication.

### Detail specification review passed

The final suite passes 203 tests across 19 files and the production build passes.
Independent specification review passed, including 16 focused delta tests after
the loading-state focus repair. Initial static JavaScript totals 681,522 bytes
versus approximately 913.7 kB before splitting; the detail/settings chunks load
on demand. All individual chunks are below 500 kB with the warning unchanged.
The favicon request now resolves from a local asset. Independent quality review passed, including 77 focused tests and a production build.


## Final loading stability and production measurements

A subsequent full production run exposed initial layout shifts of 0.293 on desktop
and 0.452 on mobile. The final correction matches loading placeholders to actual
market tiles, table rows, spotlight fields and macro entries. It reserves the
existing refresh-time row and avoids rendering both data and skeleton rows while
cached AI labels are pending. No artificial wait or whole-page minimum height is
used. Deferred-response regression coverage preserves the original request count.

Controlled delayed-API measurement at 1350px recorded workspace height 914px before
and after loading; at 412px it changed from 1526px to 1527px. Measured layout shifts
were 0.00121 and 0.00103 respectively.

| Production Lighthouse | Desktop | Mobile |
| --- | ---: | ---: |
| Performance | 100 | 92 |
| Accessibility | 96 | 96 |
| Best Practices | 100 | 100 |
| First Contentful Paint | 609 ms | 2559 ms |
| Largest Contentful Paint | 655 ms | 2719 ms |
| Total Blocking Time | 0 ms | 0 ms |
| Cumulative Layout Shift | 0.00121 | 0.00134 |

These are single local laboratory runs against fixed isolated fixtures, using
Lighthouse desktop/mobile presets. They are not field performance guarantees.
The remaining accessibility score reflects the reviewed library focus sentinels
above; manual keyboard verification passes. Raw reports remain in ignored local
artifacts. The final initial JavaScript is approximately 683.46 kB, with detail and
settings loaded on demand and each individual chunk below 500 kB.


## Final packaging review

The final frontend suite passes 204 tests across 20 files, and the production build
passes. Independent Task4 specification review passed with 23 tests across four
files and checked README claims against implementation. Eight final homepage
width/theme cases passed after the loading correction. The two 1440x960 main
screenshots and the direct settings-drawer capture were refreshed from the frozen
production build and visually inspected. README local file links resolve.

The README introduces the actual research workflow, shows light/dark runtime views,
and then presents installation and web AI configuration. Advanced environment,
API and directory details are folded for readability. Fixture provenance and local
credential storage are explicit. Repository About and topics are included in the
authorized publication scope.


### Final quality and privacy gate

Independent Task4 quality review passed with 23 tests across four files, static
review and visual inspection of all three captures. No actionable findings remain.
Both independent reviewers confirmed the refined README and screenshot provenance.
The frontend module is done. The reviewed loading fix is committed at `0c6cc07`.

Final private checks confirm the original environment, authorized local web AI
configuration, five user watchlist entries and zero holdings are preserved. The
actual credential is absent from tracked files, the diff and pending commits.
Only the owned acceptance services on 8011/5175/5177/8321 were stopped; the user's
backend on 8000 and frontend on 5173 still return HTTP 200.

Repository About now describes watchlist filtering, charts/fundamentals, holdings,
web-configured DeepSeek and themes. Existing topics were preserved and `deepseek`
was added. Visibility remains public and the default branch remains main.


## Repository delivery

- Release commit: `6f69211f5c373e83790fbbf42eabcdbc363e2b62`, normally pushed to `origin/main` without force. Remote commit identity was verified.
- [Hosted CI run 34756944059](https://github.com/BirdieMoon-peter/Investment-Board/actions/runs/34756944059) passed both `Backend and launchers` and `Frontend tests and build`, including all test/build steps for this exact commit.
- Actual public GitHub rendering was checked in Edge: the README headings render, both main screenshots decode at1440x960, and all four documented advanced sections are present with working disclosure. The additional platform-generated Mermaid control is not a project section.
- Repository About and nine topics are synchronized. The final documentation-only follow-up records these completed checks; its remote identity and hosted CI are checked separately at delivery.
