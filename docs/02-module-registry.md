# Module Registry

This registry tracks product modules. The workflow scaffold itself is already in place; use the table below for application development.

| Module | Type | Status | Doc | Last Review |
|---|---|---|---|---|
| frontend | tech-layer | done | `docs/modules/frontend.md` | 2026-09-12 |
| backend | tech-layer | doing | `docs/modules/backend.md` | 2026-09-12 |
| data-layer | tech-layer | done | `docs/modules/data-layer.md` | 2026-09-12 |
| scripts | tech-layer | done | `docs/modules/scripts.md` | 2026-09-13 |

## Status Meanings
- `todo`: not started
- `doing`: currently active module
- `review`: implementation finished, waiting for review gate
- `done`: review gate passed
- `blocked`: cannot proceed until blocker is resolved

## Registry Rules
- For this single-developer workflow, only one module should be in `doing` at a time.
- A module in `review` should keep its review evidence in its own module document.
