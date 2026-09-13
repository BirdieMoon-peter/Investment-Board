# Current Progress

## Current Focus
Repository packaging is in review: project README, two isolated-demo runtime screenshots, portable configuration, contributor guidance, CI and source-only version-control cleanup.

## Verified Application State
- Backend: 278 tests passed; real fresh AI acceptance remains blocked by provider authentication.
- Frontend: 100 tests passed; production build passed.
- Scripts: 15 tests passed; independent review and real isolated startup/stop/restart passed.
- Frontend and data-layer are done. Scripts returns to done after packaging review and publication verification.

## Remaining Work
- Finish clean-source setup and staged-tree review, then publish to the existing default branch.
- For backend completion, verify fresh demo stock/holding AI generation using an authorized available provider, then persistence/history/cache replay. Automated fixtures do not establish live provider availability.

## Evidence
- docs/verification/release-readiness.md
- Raw local logs, databases and session-specific notes stay outside version control.
