# Engineering Workflow Design

## Goal
Create a Claude Code-native engineering workflow for this project that uses persistent memory, efficient skill routing, markdown-led execution, and module-level review gates.

## Context
This directory started empty, so the workflow must establish both project control documents and persistent memory from scratch. The workflow is intended for a single developer and should organize work by technical-layer modules.

## Approved Decisions
- The workflow is optimized for a single developer.
- The workflow is Claude Code-specific rather than tool-agnostic.
- Modules are defined by technical layer.
- Markdown documents act as the project source of truth.

## Structure
### Root control
- `CLAUDE.md` defines startup behavior, document precedence, skill routing, and review-gate rules.

### Project documents
- `docs/00-workflow.md` explains the full development lifecycle.
- `docs/01-roadmap.md` tracks stage-level progress.
- `docs/02-module-registry.md` tracks module states.
- `docs/03-review-checklist.md` defines the common review gate.
- `docs/modules/*.md` define the scope and verification criteria for each technical-layer module.

### Persistent memory
- `memory/MEMORY.md` stores stable project conventions.
- `memory/progress.md` stores the current execution state.
- `memory/decisions.md` stores durable architectural and workflow decisions.

## Skill Routing Design
The workflow should route work by project phase rather than by ad hoc judgment:
- design or boundary changes -> `superpowers:brainstorming`
- approved design to implementation tasks -> `superpowers:writing-plans`
- plan execution -> `superpowers:subagent-driven-development`
- debugging -> `superpowers:systematic-debugging`
- module review -> `superpowers:requesting-code-review`
- completion validation -> `superpowers:verification-before-completion`

## Module Review Gate
A module must move through `todo -> doing -> review -> done`, with `blocked` available when work cannot continue. A module can only reach `done` after:
- implementation matches the module goal and scope
- verification items pass
- review is completed
- completion verification is completed
- docs and memory are synchronized

## Expected Outcome
After this workflow scaffold is created, the project should have a repeatable, inspectable process for choosing modules, planning work, tracking progress, and verifying module completion.
