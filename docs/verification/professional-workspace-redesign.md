# Professional workspace redesign verification

Date: 2026-09-13
Status: implementation in progress; no completion claim.

## Baseline and scope

The approved [design](../superpowers/specs/2026-09-13-professional-workspace-redesign-design.md)
and [plan](../superpowers/plans/2026-09-13-professional-workspace-redesign.md)
cover frontend theme, homepage/settings interactions and grouped stock research.
The pre-change frontend baseline passed163 tests across14 files.

The audit measured the watchlist heading below the first viewport at approximately
y1137px in a1440x960 browser, with some provider requests still loading. Opening
settings inserted approximately1058px of content above the workspace. The existing
chart used a white canvas in the dark page. These are the specific layout issues
the redesign addresses.

## Acceptance matrix

| Area | Required evidence | State |
| --- | --- | --- |
| Theme | System/light/dark, persistence, system change, portal/chart parity | Pending |
| First viewport | Watchlist header and5 demo rows at1440x900 | Pending |
| Watchlist | Filter, market selection, numeric sort/null-last, counts | Pending |
| Detail return | Restore filter,sort,scroll and correct focus | Pending |
| Search | Explicit submit,add,already-added feedback,stale response and custom code | Pending |
| Removal | Correct name,confirm,cancel,controlled failure | Pending |
| Research groups | Correct panels,draft/history retention,no automatic generation | Pending |
| Chart | Theme without range reset,resize,raw-row disclosure/pagination | Pending |
| Holdings and advice | Isolated CRUD,mock fresh advice,persistence/cache/history | Pending |
| Settings | Tab switch retention,dirty/busy close guards,focus return | Pending |
| AI configuration | Existing save,test,clear,restore and secret handling | Pending |
| Responsive | Both themes at320/390/768/1440,no document overflow | Pending |
| Accessibility | Contrast,keyboard,labels,button fit,screen-reader state | Pending |
| Lighthouse | Production preview with stable isolated fixtures; lab results only | Pending |
| Regression/review | Full frontend/build,related checks,independent spec then quality | Pending |
| Delivery | Current screenshots,README,clean Git push and hosted CI | Pending |

## Isolation

Runtime acceptance uses a new copy of the previously isolated public demo database,
never the user's database. Public historical detail data for the two original demo
securities is retained. Three additional fixed quote fixtures exercise a five-row
watchlist. External homepage/search/sync providers are replaced only in a temporary
acceptance app; production backend source is unchanged. A loopback mock model emits
clearly identified demonstration analysis and logs no credentials or user context.

Before acceptance, actual user configuration file hashes and watchlist/holdings
rows were saved privately for comparison. The user then explicitly authorized replacing the real web AI configuration with
DeepSeek official Flash (`deepseek-flash`, `https://api.deepseek.com`). The existing
protected settings API saved it successfully; its fixed-message connection test
passed in461.72ms without reading investment context. A new private hash baseline
records this authorized configuration change. The environment file and user
watchlist/holdings remain subject to the original unchanged-data check.
The real app remains on8000/5173; owned
acceptance services use8011/5175/8321. Temporary scripts/logs/data live outside the
tracked source tree.

## Design pre-flight interpretation

The requested taste skill explicitly excludes dashboards; the approved design
uses official Fluent product components. Applicable checks cover hierarchy,
typography,theme,color/shape consistency,contrast,states,keyboard,mobile and copy.
Marketing hero,photography,bento,brand walls,scroll narratives and testimonial
rules are N/A. No decorative or AI-generated images are needed in the working
investment interface; published images must be actual browser captures.

## Theme foundation increment

- Official Fluent v9, TanStack v8, Phosphor and self-hosted IBM Plex dependencies installed with compatible React19 peers.
- Dependency audit exposed existing toolchain advisories. Compatible Vite7.3.6 and Vitest4.1.11 plus patched transitive packages were verified with a clean npm ci; npm audit reports0 vulnerabilities.
- Theme tests:14 passed; frontend suite177 passed; production build passed. RED evidence records8 behavior failures before implementation.
- Actual Edge browser theme switch produced no page errors; both light/dark captures inspected. Charts and final layouts are verified in subsequent increments.
- Independent specification and quality review PASS; both reviewers independently reran14 theme tests. No unresolved findings.

## DeepSeek diagnostic acceptance

User-requested configuration authenticated successfully. A separate invented-company
and invented-position database exposed a list-field prompt ambiguity and an output
cap truncation (`finish_reason=length`). A temporary clarified prompt with4096
output tokens passed7 real route/persistence checks and2 provider calls. Neither
real watchlist nor holdings were sent. This diagnostic is not final product-code
acceptance; Task2b incorporates the fix, then repeats without the temporary patch.

Supporting regressions currently pass:382 backend tests and15 launcher/smoke tests.
The first scripts run was blocked from binding a loopback port by the sandbox;
the same tests passed when run with local-listening permission.

## Initial homepage visual check

The initial desktop layout showed all5 watchlist rows within1440x900 (last row
bottom827px);390px view had no document overflow. The compact header was further
adjusted to the approved64px height. Final acceptance follows the frozen code.

Axe flagged Fluent/Tabster's own `data-tabster-dummy` focus sentinel elements for
`aria-hidden-focus`. These are recorded separately with raw results retained;
application elements are still checked under the same rule. This library pattern
is tracked in [Fluent issue27517](https://github.com/microsoft/fluentui/issues/27517).
No focus sentinels or accessibility rules are removed to raise audit scores.
A real browser also exposed nested confirmation focus restoration, which is
being repaired and will be retested before homepage acceptance.

### Frozen homepage and drawer browser pass

- Settings guard probe:6 checks passed, including lazy mounting, cross-tab draft
  retention, Escape/continue, discard/unmount/reopen and all three busy dismissal
  routes. Four settings widths pass without overflow; no page errors.
- Homepage:both themes at320/390/768/1440 pass with64px header and no document
  overflow. Axe flags only the documented Fluent/Tabster sentinel pattern.
- Immediate post-theme screenshots initially captured Fluent's short color
  transition. Fresh dark loads render correct foreground colors; final captures
  await active transition completion. No source change was needed for this.
- Independent specification review found a filtered-out spotlight return-focus
  case. That regression is being repaired before quality review.

### Homepage increment complete

193 frontend tests and production build pass. Independent specification and quality
reviews pass. The spotlight focus omission is fixed and covered by two RED/GREEN
regressions. Actual browser checks pass:6 drawer guards,6 watchlist flows and5
sync/cache/error/empty states. Temporary custom-code add/remove returned the
isolated demo database to its five-row baseline.

Initial desktop production Lighthouse:Performance100,Accessibility96,Best
Practices96;FCP645ms,LCP689ms,TBT0ms,CLS0.0156. This is a lab baseline, not a field
CWV claim. Accessibility flags the recorded library sentinels; the console error
is a missing favicon. Final assets/loading and mobile results follow Task3/4.

### DeepSeek product-code acceptance complete

The diagnostic monkeypatch was removed. Final source passed7 actual route and
persistence checks with official `deepseek-flash`:2 fresh calls (stock7.69s,
holding10.65s), cache reuse with zero extra calls, history and new-app persisted
reads. Only invented company/quote/position data was sent. Both independent
reviews pass;41 provider tests and386 full backend tests pass. The current
account's prior integration blocker is resolved. This verifies functionality,
not investment accuracy or guaranteed future provider availability.

The new AI settings interface also passed10 actual browser checks with invented
keys and the loopback mock; the isolated saved override was reset afterwards.
