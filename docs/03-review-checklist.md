# Review Checklist

Use this checklist whenever a module reaches `review`.

## 1. Scope Check
- [ ] The implementation matches the module `Goal`
- [ ] No work outside the module `Scope` was introduced without updating docs
- [ ] All planned tasks are complete, or unfinished tasks are explicitly documented

## 2. Functional Check
- [ ] Core module behavior runs successfully
- [ ] Key inputs and outputs match expectations
- [ ] Important failure paths have been checked
- [ ] Module-specific verification items in the module document are complete

## 3. Regression Check
- [ ] Related commands, flows, or integrations still work
- [ ] The module did not break dependent modules
- [ ] New behavior does not conflict with existing project decisions

## 4. Documentation and Memory Check
- [ ] Module document is updated with the latest status
- [ ] `docs/02-module-registry.md` is updated
- [ ] `memory/progress.md` reflects the next step
- [ ] Stable decisions are recorded in `memory/MEMORY.md` or `memory/decisions.md`

## 5. Required Claude Code Skills
- [ ] `superpowers:requesting-code-review` has been run
- [ ] `superpowers:verification-before-completion` has been run

## 6. Final Decision
- [ ] The module may move from `review` to `done`
- [ ] `Last Review` has been recorded in `docs/02-module-registry.md`
