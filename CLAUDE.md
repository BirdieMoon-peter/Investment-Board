# Investment Board Claude Workflow

## Source of Truth
1. `docs/00-workflow.md`
2. `docs/01-roadmap.md`
3. `docs/02-module-registry.md`
4. `docs/modules/*.md`
5. `memory/MEMORY.md`
6. `memory/progress.md`

If documents disagree, prefer the more specific document in this order:
- module document over roadmap
- roadmap over workflow overview
- progress for current working state only

`memory/progress.md` tracks execution state only. It must not redefine scope, requirements, or module boundaries.

## Startup Routine
At the start of each session:
1. Read `docs/00-workflow.md`
2. Read `docs/01-roadmap.md`
3. Read `docs/02-module-registry.md`
4. Read `memory/MEMORY.md`
5. Read `memory/progress.md`
6. Open the current module document before changing code

## Skill Routing
- Requirement changes or boundary changes -> `superpowers:brainstorming`
- Turn approved design into execution tasks -> `superpowers:writing-plans`
- Execute a written plan -> `superpowers:subagent-driven-development`
- Execute in current session without subagents only if needed -> `superpowers:executing-plans`
- Bug, failing test, unexpected behavior -> `superpowers:systematic-debugging`
- Module implementation finished -> `superpowers:requesting-code-review`
- Before claiming completion -> `superpowers:verification-before-completion`

## Module State Rules
- Allowed states: `todo`, `doing`, `review`, `done`, `blocked`
- A module cannot move to `done` until review and verification both pass
- Every module must have its own markdown document in `docs/modules/`

## Required Updates
Update `memory/progress.md` when:
- starting a module
- finishing a meaningful task inside a module
- entering review
- finishing review

Update `docs/02-module-registry.md` when:
- module status changes
- module ownership focus changes
- a review result changes module state

Update the module document when:
- scope changes
- tasks are added or removed
- verification steps change
- open questions are resolved

## Review Gate
When a module is ready:
1. Set module state to `review`
2. Update the module document with actual verification notes
3. Run `superpowers:requesting-code-review`
4. Run `superpowers:verification-before-completion`
5. Sync `docs/02-module-registry.md` and `memory/progress.md`
6. Only then move the module to `done`

## Development Style
- Follow markdown documents before writing code
- Keep changes scoped to the active module
- Do not silently expand scope beyond the module document
- Prefer small, reviewable module increments
