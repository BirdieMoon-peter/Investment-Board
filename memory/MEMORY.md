# Project Memory

## Project Goal
Maintain a Claude Code-native, markdown-led engineering workflow for the Investment Board project.

## Stable Structure
- Workflow rules live in `CLAUDE.md`
- Global process lives in `docs/00-workflow.md`
- Project sequencing lives in `docs/01-roadmap.md`
- Module state lives in `docs/02-module-registry.md`
- Shared review gate lives in `docs/03-review-checklist.md`
- Module definitions live in `docs/modules/*.md`
- Current execution state lives in `memory/progress.md`
- Stable decisions live in `memory/decisions.md`

## Module Boundaries
- `frontend`
- `backend`
- `data-layer`
- `scripts`

## Workflow Rules
- Start each session by reading workflow, roadmap, module registry, and memory files.
- Open the active module document before changing implementation files.
- Keep work scoped to one module at a time.
- A module cannot move to `done` until it passes the review gate.

## Skill Rules
- Use `superpowers:brainstorming` for requirement or structure changes.
- Use `superpowers:writing-plans` before substantial implementation work.
- Use `superpowers:subagent-driven-development` to execute approved plans when possible.
- Use `superpowers:systematic-debugging` for bugs, failing tests, or unexpected behavior.
- Use `superpowers:requesting-code-review` for completed module work.
- Use `superpowers:verification-before-completion` before claiming work is complete.
