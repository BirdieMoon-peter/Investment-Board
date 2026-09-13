# Engineering Workflow Foundation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the initial markdown-led Claude Code workflow scaffold for this project, including memory, module registry, and review-gate files.

**Architecture:** Keep workflow control in a small set of root and `docs/` markdown files, while using `memory/` to separate durable conventions from current progress. Each technical-layer module gets its own markdown file so module scope, verification, and status can be managed independently.

**Tech Stack:** Markdown, Claude Code workflow conventions, project-local memory files.

---

## Chunk 1: Control Documents

### Task 1: Create the root workflow rules

**Files:**
- Create: `CLAUDE.md`
- Test: manual read of `CLAUDE.md`

- [ ] **Step 1: Draft the root workflow rules**

```md
# Investment Board Claude Workflow

## Startup Routine
1. Read workflow docs
2. Read memory files
3. Open the active module doc
```

- [ ] **Step 2: Verify the rules file is missing before creation**

Run: `test -f "CLAUDE.md" && echo exists || echo missing`
Expected: `missing`

- [ ] **Step 3: Create `CLAUDE.md` with startup, skill routing, update, and review rules**

```md
## Skill Routing
- design changes -> brainstorming
- implementation planning -> writing-plans
- debugging -> systematic-debugging
```

- [ ] **Step 4: Read the file to verify required sections exist**

Run: `python - <<'PY'
from pathlib import Path
text = Path('CLAUDE.md').read_text()
for section in ['Source of Truth', 'Startup Routine', 'Skill Routing', 'Review Gate']:
    assert section in text, section
print('ok')
PY`
Expected: `ok`

## Chunk 2: Project Control Docs

### Task 2: Create the workflow, roadmap, registry, and review checklist docs

**Files:**
- Create: `docs/00-workflow.md`
- Create: `docs/01-roadmap.md`
- Create: `docs/02-module-registry.md`
- Create: `docs/03-review-checklist.md`
- Test: manual read of those four files

- [ ] **Step 1: Create the workflow overview**
- [ ] **Step 2: Create the roadmap document**
- [ ] **Step 3: Create the module registry document**
- [ ] **Step 4: Create the shared review checklist**
- [ ] **Step 5: Verify all four files exist**

Run: `python - <<'PY'
from pathlib import Path
paths = [
'docs/00-workflow.md',
'docs/01-roadmap.md',
'docs/02-module-registry.md',
'docs/03-review-checklist.md',
]
for p in paths:
    assert Path(p).exists(), p
print('ok')
PY`
Expected: `ok`

## Chunk 3: Module Documents

### Task 3: Create technical-layer module documents

**Files:**
- Create: `docs/modules/frontend.md`
- Create: `docs/modules/backend.md`
- Create: `docs/modules/data-layer.md`
- Create: `docs/modules/scripts.md`
- Test: manual read of module files

- [ ] **Step 1: Create the frontend module doc**
- [ ] **Step 2: Create the backend module doc**
- [ ] **Step 3: Create the data-layer module doc**
- [ ] **Step 4: Create the scripts module doc**
- [ ] **Step 5: Verify each module doc includes Goal, Scope, Tasks, Current Status, Recommended Skills, and Verification**

Run: `python - <<'PY'
from pathlib import Path
required = ['## Goal', '## Scope', '## Tasks', '## Current Status', '## Recommended Skills', '## Verification']
for p in [
'docs/modules/frontend.md',
'docs/modules/backend.md',
'docs/modules/data-layer.md',
'docs/modules/scripts.md',
]:
    text = Path(p).read_text()
    for item in required:
        assert item in text, (p, item)
print('ok')
PY`
Expected: `ok`

## Chunk 4: Memory and Planning Docs

### Task 4: Create memory files and workflow meta-docs

**Files:**
- Create: `memory/MEMORY.md`
- Create: `memory/progress.md`
- Create: `memory/decisions.md`
- Create: `docs/superpowers/specs/2026-03-10-engineering-workflow-design.md`
- Create: `docs/superpowers/plans/2026-03-10-engineering-workflow-foundation.md`
- Test: manual read of memory and meta-docs

- [ ] **Step 1: Create stable memory file**
- [ ] **Step 2: Create current progress file**
- [ ] **Step 3: Create decision log**
- [ ] **Step 4: Create design doc summarizing approved workflow decisions**
- [ ] **Step 5: Create implementation plan doc for future reuse**
- [ ] **Step 6: Verify all files exist and key headers are present**

Run: `python - <<'PY'
from pathlib import Path
checks = {
'memory/MEMORY.md': '# Project Memory',
'memory/progress.md': '# Current Progress',
'memory/decisions.md': '# Decisions',
'docs/superpowers/specs/2026-03-10-engineering-workflow-design.md': '# Engineering Workflow Design',
'docs/superpowers/plans/2026-03-10-engineering-workflow-foundation.md': '# Engineering Workflow Foundation Implementation Plan',
}
for p, header in checks.items():
    text = Path(p).read_text()
    assert header in text, (p, header)
print('ok')
PY`
Expected: `ok`

## Chunk 5: Final Verification

### Task 5: Verify scaffold consistency

**Files:**
- Modify: `memory/progress.md`
- Test: consistency verification across all workflow files

- [ ] **Step 1: Verify the expected scaffold file set exists**

Run: `python - <<'PY'
from pathlib import Path
expected = [
'CLAUDE.md',
'docs/00-workflow.md',
'docs/01-roadmap.md',
'docs/02-module-registry.md',
'docs/03-review-checklist.md',
'docs/modules/frontend.md',
'docs/modules/backend.md',
'docs/modules/data-layer.md',
'docs/modules/scripts.md',
'memory/MEMORY.md',
'memory/progress.md',
'memory/decisions.md',
'docs/superpowers/specs/2026-03-10-engineering-workflow-design.md',
'docs/superpowers/plans/2026-03-10-engineering-workflow-foundation.md',
]
root = Path('project root')
for rel in expected:
    assert (root / rel).exists(), rel
print('ok')
PY`
Expected: `ok`

- [ ] **Step 2: Update `memory/progress.md` with the verified current state**

```md
## Next Step
Choose the first technical-layer module to start.
```

- [ ] **Step 3: Read the key control docs and confirm they agree on module names and review rules**

Run: `python - <<'PY'
from pathlib import Path
root = Path('project root')
texts = {
'workflow': (root / 'docs/00-workflow.md').read_text(),
'registry': (root / 'docs/02-module-registry.md').read_text(),
'memory': (root / 'memory/MEMORY.md').read_text(),
}
for module in ['frontend', 'backend', 'data-layer', 'scripts']:
    assert all(module in t for t in texts.values()), module
assert 'review' in texts['workflow']
assert 'done' in texts['registry']
print('ok')
PY`
Expected: `ok`
