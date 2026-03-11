# Engineering Workflow

## 1. Principles
- Document-first: read and update markdown before implementation changes.
- Module-by-module delivery: work one technical-layer module at a time.
- Memory-backed continuity: keep current state in `memory/` so work resumes cleanly.
- Review before done: every module must pass a review gate.

## 2. Source of Truth
- Global workflow: `docs/00-workflow.md`
- Project roadmap: `docs/01-roadmap.md`
- Module registry: `docs/02-module-registry.md`
- Shared review gate: `docs/03-review-checklist.md`
- Module definitions: `docs/modules/*.md`
- Stable memory: `memory/MEMORY.md`
- Current progress: `memory/progress.md`
- Decision log: `memory/decisions.md`

## 3. Module Boundaries
The default technical-layer modules for this project are:
- `frontend`
- `backend`
- `data-layer`
- `scripts`

Any new module should be added to `docs/02-module-registry.md`, given its own document in `docs/modules/`, and reflected in stable memory if it becomes part of the standard project structure.

## 4. Development Lifecycle
1. Choose the current module from `docs/02-module-registry.md`.
2. Read the matching module document in `docs/modules/`.
3. Update `memory/progress.md` with current focus and next step.
4. If requirements or boundaries are unclear, use `superpowers:brainstorming`.
5. If implementation needs a task list, use `superpowers:writing-plans`.
6. Implement only the approved module scope.
7. If a bug or failing test appears, use `superpowers:systematic-debugging`.
8. When the module is feature-complete, move it to `review`.
9. Run the review gate in `docs/03-review-checklist.md`.
10. If the module passes review, move it to `done` and sync docs and memory.

## 5. Skill Routing
| Scenario | Required Skill | Expected Output |
|---|---|---|
| New requirement or design change | `superpowers:brainstorming` | approved design direction |
| Convert design into work items | `superpowers:writing-plans` | implementation plan |
| Execute an approved plan | `superpowers:subagent-driven-development` | completed implementation tasks |
| Debug unexpected behavior | `superpowers:systematic-debugging` | root cause and repair path |
| Review completed module | `superpowers:requesting-code-review` | review findings |
| Confirm completion | `superpowers:verification-before-completion` | evidence-based completion check |

## 5. Review Gate
A module may move from `review` to `done` only when all of the following are true:
- the implementation matches the module goal and scope
- the module verification checklist passes
- no known blocker remains open
- docs and memory are updated
- review and completion verification have both been run
- review evidence is recorded in the active module document

Review evidence must be stored in the active module document under `## Review Evidence`, including:
- review date
- commands or checks used for verification
- result summary
- remaining follow-up items, if any

## 6. Update Rules
### Start of module work
Update:
- `docs/02-module-registry.md`
- the module document
- `memory/progress.md`

### Scope or design change
Update:
- the active module document
- `docs/01-roadmap.md` if the change affects project order or milestones
- `memory/decisions.md` if the change is a stable decision

### Enter review
Update:
- module document status
- registry status
- progress memory

### Finish review
Update:
- registry status
- progress memory
- stable memory if a repeatable rule or convention was confirmed
