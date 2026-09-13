# Release readiness

Verified locally on 2026-09-13 during repository packaging.

| Check | Result |
|---|---|
| Backend API, services and persistence | 278 tests passed |
| Frontend components, interactions and lifecycle | 100 tests passed across 11 files |
| Launchers and isolated smoke lifecycle | 15 tests passed |
| Frontend production build | Passed |
| Independent packaging configuration/provider/seed checks | 36 tests passed |
| Actual startup, shutdown and restart | Verified with owned-process cleanup |
| README screenshots | Captured from the actual application using a separate demo database |

The GitHub workflow runs the deterministic backend, launcher and frontend checks on a clean Ubuntu runner. Hosted Ubuntu CI subsequently passed both jobs for publication commit `47c338fe7deb2ede8201e34470014d152626baa7`: [CI run](https://github.com/BirdieMoon-peter/Investment-Board/actions/runs/34747255729). Local and hosted results are separate evidence.

Fresh AI generation requires a configured and authenticated external model provider. Current live-provider acceptance remains blocked by authentication; successful mocks, cached history and page rendering do not prove fresh generation. No real user watchlist or holdings were used in screenshot preparation or model probes.

Repository maintenance removes dependencies, caches, runtime databases, logs and local private verification records from the current tracked tree while retaining local files. It does not rewrite earlier Git history. No license or change in repository visibility is introduced.

## Clean-source installation check

The staged source tree was exported without dependencies, databases or local configuration. A new Python3.12 virtual environment installed the package with `pip install -e './backend[dev]'`; frontend dependencies were installed with `npm ci --prefix frontend`. The new environment passed278backend tests,100frontend tests,15launcher tests, the frontend build and the real isolated smoke entrypoint. README relative links were checked, and both JPEG screenshot files were visually inspected.

Independent packaging review scanned all248tracked files: no runtime/dependency paths, credential-pattern findings, personal absolute paths or broken Markdown links. Existing private raw logs remain local.
