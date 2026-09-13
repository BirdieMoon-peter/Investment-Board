# Watchlist MVP Frontend Foundation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the frontend UI for the watchlist MVP so a user can search securities, add/remove watchlist items, and view the watchlist list rendered from the completed backend APIs.

**Architecture:** Create a minimal React + Vite + TypeScript frontend workspace in `frontend/` with one page and a small set of focused components. Keep state local to the watchlist page, isolate backend calls in a small API client module, and render empty/error/missing-quote states explicitly so the UI remains aligned with the approved MVP scope.

**Tech Stack:** React, Vite, TypeScript, Testing Library, Vitest.

---

## File Structure

### Existing files to modify
- Modify: `docs/modules/frontend.md` — record actual frontend files, verification commands, and review evidence.
- Modify: `docs/02-module-registry.md` — move `frontend` from `doing` to `review`, then to `done` after review passes.
- Modify: `memory/progress.md` — keep execution state and next handoff step in sync.
- Modify: `memory/decisions.md` — record stable frontend contract decisions if confirmed during implementation.

### New frontend workspace files
- Create: `frontend/package.json` — frontend dependencies and scripts.
- Create: `frontend/tsconfig.json` — TypeScript config.
- Create: `frontend/vite.config.ts` — Vite + Vitest config.
- Create: `frontend/index.html` — Vite entry HTML.
- Create: `frontend/src/main.tsx` — React entrypoint.
- Create: `frontend/src/App.tsx` — top-level app shell.
- Create: `frontend/src/styles.css` — minimal page and component styles.
- Create: `frontend/src/api/watchlist.ts` — backend fetch wrappers for search, add/remove, and list.
- Create: `frontend/src/types/watchlist.ts` — shared frontend API response types.
- Create: `frontend/src/components/SearchBox.tsx` — search input, search results, and add action UI.
- Create: `frontend/src/components/WatchlistTable.tsx` — list rendering, remove action, and missing-quote display.
- Create: `frontend/src/components/StatusMessage.tsx` — empty, error, and informational state component.

### New test files
- Create: `frontend/src/App.test.tsx` — top-level interaction flow tests for search, add, remove, and refresh.
- Create: `frontend/src/components/SearchBox.test.tsx` — search UI state tests.
- Create: `frontend/src/components/WatchlistTable.test.tsx` — table rendering and remove interaction tests.
- Create: `frontend/src/test/setup.ts` — test setup for DOM matchers and fetch mocking.

### Explicitly deferred files
- Do not create routing, stock detail pages, grouped watchlists, or charting components.
- Do not add Zustand, TanStack Query, or shadcn/ui in this first frontend slice.
- Do not add auth/session flows.
- Do not add real-time polling or websocket support.

## Chunk 1: Frontend Workspace and Watchlist Page Shell

### Task 1: Create the frontend workspace and top-level watchlist page shell

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/App.test.tsx`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Create the frontend package metadata and dev tooling**

```json
{
  "name": "investment-board-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.2.0",
    "@testing-library/user-event": "^14.5.2",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "jsdom": "^25.0.1",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.4"
  }
}
```

- [ ] **Step 2: Write the failing top-level app test**

```tsx
import { render, screen } from "@testing-library/react";

import App from "./App";


test("renders watchlist MVP shell", () => {
  render(<App />);

  expect(screen.getByRole("heading", { name: /watchlist/i })).toBeInTheDocument();
  expect(screen.getByPlaceholderText(/search by code or name/i)).toBeInTheDocument();
});
```

- [ ] **Step 3: Install frontend dependencies**

Run: `npm install --prefix "frontend"`
Expected: install completes with React, Vite, TypeScript, and Testing Library packages

- [ ] **Step 4: Run the app test to verify it fails before implementation**

Run: `npm test --prefix "frontend" -- --runInBand`
Expected: FAIL with missing `App` or missing frontend workspace files

- [ ] **Step 5: Implement the minimal frontend shell and test setup**

```tsx
export default function App() {
  return (
    <main>
      <h1>Watchlist</h1>
      <input placeholder="Search by code or name" />
      <section aria-label="watchlist results" />
    </main>
  );
}
```

- [ ] **Step 6: Re-run the app test**

Run: `npm test --prefix "frontend" -- --runInBand`
Expected: PASS

## Chunk 2: API Client, Search/Add UI, and Watchlist Rendering

### Task 2: Add frontend API client and search interaction flow

**Files:**
- Create: `frontend/src/api/watchlist.ts`
- Create: `frontend/src/types/watchlist.ts`
- Create: `frontend/src/components/SearchBox.tsx`
- Create: `frontend/src/components/SearchBox.test.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/components/SearchBox.test.tsx`

- [ ] **Step 1: Write the failing search component test**

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SearchBox } from "./SearchBox";


test("searches and renders backend results", async () => {
  const user = userEvent.setup();
  const onAdd = vi.fn();
  global.fetch = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify([
        {
          security_id: 1,
          market: "SZ",
          code: "000001",
          name: "Ping An Bank",
          industry: "Banking",
          status: "active"
        }
      ])
    )
  ) as Mock;

  render(<SearchBox onAdd={onAdd} />);
  await user.type(screen.getByPlaceholderText(/search by code or name/i), "000001");
  await user.click(screen.getByRole("button", { name: /search/i }));

  expect(await screen.findByText(/Ping An Bank/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the search component test to verify it fails before implementation**

Run: `npm test --prefix "frontend" -- SearchBox.test.tsx`
Expected: FAIL with missing component or API client

- [ ] **Step 3: Implement the frontend API client and shared response types**

```ts
export async function searchSecurities(query: string): Promise<SecuritySearchResult[]> {
  const response = await fetch(`/api/watchlist/securities/search?query=${encodeURIComponent(query)}`);
  if (!response.ok) {
    throw new Error("Failed to search securities");
  }
  return response.json();
}
```

- [ ] **Step 4: Implement the search UI with explicit empty and error states**

```tsx
export function SearchBox({ onAdd }: { onAdd: (securityId: number) => Promise<void> | void }) {
  // local query state
  // local loading state
  // local results state
  // render button, no-results state, and add buttons
}
```

- [ ] **Step 5: Re-run the search component test**

Run: `npm test --prefix "frontend" -- SearchBox.test.tsx`
Expected: PASS

### Task 3: Implement the watchlist list rendering and remove interaction

**Files:**
- Create: `frontend/src/components/WatchlistTable.tsx`
- Create: `frontend/src/components/StatusMessage.tsx`
- Create: `frontend/src/components/WatchlistTable.test.tsx`
- Modify: `frontend/src/api/watchlist.ts`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/components/WatchlistTable.test.tsx`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing table component test**

```tsx
import { render, screen } from "@testing-library/react";

import { WatchlistTable } from "./WatchlistTable";


test("renders missing-quote fallback when quote fields are null", () => {
  render(
    <WatchlistTable
      rows={[
        {
          security_id: 1,
          code: "000001",
          name: "Ping An Bank",
          industry: "Banking",
          last_price: null,
          change_percent: null,
          snapshot_time: null,
        },
      ]}
      onRemove={async () => {}}
    />
  );

  expect(screen.getByText(/pending quote/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the table/app tests to verify they fail before implementation**

Run: `npm test --prefix "frontend" -- WatchlistTable.test.tsx App.test.tsx`
Expected: FAIL with missing table component or missing app behavior

- [ ] **Step 3: Implement fetchWatchlist/addWatchlistItem/removeWatchlistItem client functions**

```ts
export async function fetchWatchlist(): Promise<WatchlistRow[]> { /* GET /api/watchlist/items */ }
export async function addWatchlistItem(securityId: number): Promise<WatchlistItemResponse> { /* POST /api/watchlist/items */ }
export async function removeWatchlistItem(securityId: number): Promise<void> { /* DELETE /api/watchlist/items/{security_id} */ }
```

- [ ] **Step 4: Implement the table, status messages, and top-level App interaction flow**

```tsx
// App loads watchlist on mount
// SearchBox calls add handler then reloads the list
// WatchlistTable calls remove handler then reloads the list
// StatusMessage renders empty / error / info messages
```

- [ ] **Step 5: Re-run the table/app tests**

Run: `npm test --prefix "frontend" -- WatchlistTable.test.tsx App.test.tsx`
Expected: PASS

## Chunk 3: Frontend Verification and Review-State Sync

### Task 4: Run frontend verification and sync review-state docs

**Files:**
- Modify: `docs/modules/frontend.md`
- Modify: `docs/02-module-registry.md`
- Modify: `memory/progress.md`
- Modify: `memory/decisions.md`
- Test: `frontend/src/**/*.test.tsx`

- [ ] **Step 1: Run the full frontend test suite**

Run: `npm test --prefix "frontend"`
Expected: all tests PASS

- [ ] **Step 2: Record stable frontend decisions if confirmed**

Add to `memory/decisions.md`:

```md
- 2026-03-10: The watchlist MVP frontend uses a small local-state React app instead of introducing global state libraries.
- 2026-03-10: The frontend renders explicit empty, no-result, error, and missing-quote states for the watchlist MVP.
```

- [ ] **Step 3: Update the frontend module doc with actual implementation scope and verification commands**

Add or update these points in `docs/modules/frontend.md`:

```md
## Verification
- `npm test --prefix "frontend"`
- search UI verified for result rendering, no-result state, and add action behavior
- watchlist list UI verified for joined backend data, remove behavior, and missing-quote fallback
- top-level app flow verified for initial load, refresh after add/remove, and visible empty/error states
```

- [ ] **Step 4: Move the active module into review and update progress memory**

Update:
- `docs/02-module-registry.md`: set `frontend` to `review`
- `memory/progress.md`: set the next step to either scripts planning or broader MVP integration verification

- [ ] **Step 5: Run `@superpowers:requesting-code-review` for the completed frontend module**

Expected: review findings are recorded and required fixes are applied before completion claims

- [ ] **Step 6: Run `@superpowers:verification-before-completion` before moving the module to done**

Expected: evidence-based verification confirms the frontend module is ready for completion

- [ ] **Step 7: If both review skills pass, mark the module done and record the review date**

Update:
- `docs/02-module-registry.md`: set `frontend` to `done` and fill `Last Review`
- `memory/progress.md`: set the next active planning target according to the next approved module

## Final Notes
- Keep all frontend changes scoped to the approved watchlist MVP UI. Do not add charts, grouped watchlists, or stock detail pages in this plan.
- If backend contract changes become necessary during execution, stop and re-plan rather than mutating backend scope silently.
- If git is initialized before execution, create one commit per chunk after the relevant frontend test suite passes. If git is still not initialized, skip commit steps rather than inventing git history.
