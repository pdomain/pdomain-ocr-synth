---
Status: implemented
Owner: CT
Created: 2026-09-17
Last verified: 2026-09-17
Kind: plan
---

# Region Review Surface Implementation Plan

> **Shipped 2026-09-17** in `pdomain-ocr-labeler-spa`, merged as `b8c2cd7`. All seven tasks landed,
> and a Playwright test drives the whole review loop in a real browser.
>
> **The whole-branch review found two defects no task-scoped review could see, both fixed before
> merge.** A decision could be sent twice: the keyboard and the panel held separate mutation
> instances with no shared pending state, and the reject route appended a duplicate decision each
> time. The fix shares one `mutationKey` across all four region mutations, guards both paths on it,
> and makes a repeat reject a no-op. And a region selection outlived its page, so a keyboard accept
> could reach the new page's route with the old page's proposal id. The fix clears a region
> selection on page change and checks the selected id is on the current page before acting.
>
> **Corrections made during execution are marked inline.** Tasks 1 and 2 had to change consumers the
> plan did not name. The role-list check needed the exhaustive `Record` idiom. `onComplete` had to be
> extended to receive the terminal event. The run toasts matched the warning text case-sensitively
> and would have missed the capitalised early-return message.
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking. Dispatch `writing-typescript:ts-implementer` for Tasks 1
> to 5 and 7, and `writing-python:python-implementer` for the backend half of Task 6.
>
> **How this plan differs from the slice 4 plan.** It fixes every contract a task hands to the next,
> exactly: type names, store functions, hook signatures, route paths, keys and test assertions. It
> does not pre-write the body of every React component. The slice 4 plan pre-wrote its code and
> execution found twelve errors in it, five of them only by running that code against the real
> classes. This frontend has a mocked canvas library, Zustand vanilla stores and MSW handlers whose
> exact shapes an implementer reads in minutes, so each task instead names the verified existing
> file to copy the pattern from.

**Goal:** Let a person select a region or a proposal on the canvas and decide it from the keyboard
— accept, accept as another role, reject — and start the page-kind and region proposal runs from
the UI.

**Architecture:** Regions become a fifth rail target. Under that target a canvas click hit-tests
confirmed regions and proposals, smallest area first, and sets a new `region` selection level. A
`RegionDetail` panel shows the selection and calls the region routes through a new mutations hook
that invalidates the page query the way every other mutation does. A review hotkey hook adds `n`,
`p`, `enter`, `x` and `delete`, advancing to the next undecided proposal after each decision. Two
book actions start the runs through the existing job-progress toast pattern.

**Tech Stack:** React 19, TypeScript, Vite, TanStack Query, Zustand vanilla stores, Konva through
`@pdomain/pdomain-ui`, Vitest with MSW, Playwright through pytest; Python and FastAPI for Task 6's
backend half.

**Spec:** [Region review surface](../specs/2026-09-17-region-review-surface-design.md).

## Agent Index

- **Kind:** plan
- **Status:** implemented
- **Owner:** CT
- **Created:** 2026-09-17
- **Last verified:** 2026-09-17
- **Provenance:** authored 2026-09-17 from the design above and direct inspection of
  `pdomain-ocr-labeler-spa` `frontend/src/stores/selection-store.ts`, `lib/selection-walk.ts`,
  `stores/rail-store.ts`, `hooks/useRailHotkeys.ts`, `components/PageImageCanvas.tsx`,
  `api/types.ts`, `package.json`, and backend `api/regions.py`, `api/projects.py`, `api/pages.py`,
  `core/jobs/runner.py`, `core/jobs/handlers/propose_regions.py`
- **Disposition:** Implemented. Merged 2026-09-17 in `pdomain-ocr-labeler-spa` `b8c2cd7`, with
  1728 frontend tests, 1697 backend tests and both region browser tests passing.
- **Read when:** building the region review surface, or adding a rail target, selection level or
  review hotkey.
- **Search terms:** slice 3, region review, RegionDetail, useRegionMutations, useProposalRuns,
  useRegionReviewHotkeys, rail target region, hitTestRegions.

## Global Constraints

- All frontend work is under `pdomain-ocr-labeler-spa/frontend/`. The frontend gate, run from that
  directory, is:
  - `mise exec -- pnpm exec vitest run <file>` for a focused test;
  - `mise exec -- pnpm test` for the whole Vitest suite;
  - `mise exec -- pnpm run typecheck`, `mise exec -- pnpm run lint`,
    `mise exec -- pnpm run format:check`.
  `pnpm` is not on `PATH`; reach it through `mise`, as the Makefile does.
- Committing needs the Python venv on `PATH`, from the repo root:
  `export PATH="$PWD/.venv-container/bin:$PATH"`. The pre-commit hook runs `tsc -b --noEmit`,
  ESLint and Prettier on staged frontend files.
- Commit subjects must stay within 72 characters or gitlint rejects the commit.
- **Never suppress.** No `@ts-ignore`, `@ts-expect-error`, `eslint-disable`, `any` or `as unknown
  as`. Fix the types.
- **Every mutation invalidates, never writes the cache.** Invalidate `["page", projectId,
  pageIndex]` on success, as `hooks/useLineMutations.ts` does. The routes return a full
  `PagePayload`; do not write it with `setQueryData`.
- **Review keys must not collide with an always-on listener.** `useRailHotkeys` is a raw `document`
  listener on `1` to `4`, `v`, `r`, `a`, `e`. `useMatchesHotkeys` is registered unconditionally in
  `ProjectPage.tsx` on `j`, `k`, `v`, `u`, `d`, `o`, `g`, `m`, `r`. The review keys are `5`, `n`,
  `p`, `enter`, `x`, `delete`, and nothing else.
- Region and proposal types come from the generated `components["schemas"]` in `src/api/types.ts`:
  `RegionView`, `RegionProposalView`, `RegionRole`, `BBox`, `PagePayload`. Never hand-write a copy.
- The backend suite baseline is whatever `master` shows when Task 6 starts; run it before and after.

## File Structure

| file | responsibility | task |
| --- | --- | --- |
| `src/stores/rail-store.ts` | `RailTarget` gains `"region"` | 1 |
| `src/components/shell/Rail.tsx` | four exhaustive `Record<RailTarget, string>` maps gain `region`; a visible region target cell | 1, 2 |
| `src/lib/bbox-select.ts` | `targetToLayerKey` handles `region`, falling back to words for a drag | 1 |
| `src/hooks/useRailHotkeys.ts` | key `5` selects the region target | 1 |
| `src/lib/selection-walk.ts` | `SelectionLevel` gains `"region"`; `SelectionPath` gains `regionId`, `proposalId` | 1 |
| `src/stores/selection-store.ts` | `selectRegion`, `selectProposal` | 1 |
| `src/components/shell/RightPanel.tsx` | `LEVEL_PLACEHOLDER` entry; route `region` to `RegionDetail` | 1, 4 |
| `src/components/shell/Breadcrumb.tsx` | a region or proposal chip | 1 |
| `src/lib/region-hit-test.ts` | new: `regionCandidates`, `hitTestRegions`, `orderedUndecidedProposals` | 2 |
| `src/components/PageImageCanvas.tsx` | region target hit-test; selected-region highlight | 2 |
| `src/hooks/useRegionMutations.ts` | new: accept, reject, edit, delete | 3 |
| `src/hooks/useProposalRuns.ts` | new: start the page-kind and region runs | 3 |
| `src/test/handlers.ts` | MSW handlers for the region routes | 3 |
| `src/components/right-panel/RegionDetail.tsx` | new: the panel | 4 |
| `src/hooks/useRegionReviewHotkeys.ts` | new: `n`, `p`, `enter`, `x`, `delete` with auto-advance | 5 |
| `src/lib/hotkeyMap.ts` | register the review keys and `5` | 5 |
| `src/components/PageActionsCompact.tsx` | the two book actions | 6 |
| backend `core/jobs/handlers/propose_regions.py` | a summary terminal message | 6 |
| backend `tests/e2e/test_region_review_loop.py` | new: the whole loop in a browser | 7 |

`region-hit-test.ts` is a pure module on purpose. The ordering and tie-break rules are the part most
likely to be wrong, and a pure function over `RegionView[]` tests them without mounting the mocked
canvas.

---

### Task 1: The region target and the region selection level

**Files:** `src/stores/rail-store.ts`, `src/hooks/useRailHotkeys.ts`, `src/lib/selection-walk.ts`,
`src/stores/selection-store.ts`, `src/components/shell/RightPanel.tsx`,
`src/components/shell/Breadcrumb.tsx`, and their existing test files.

**Interfaces — Produces:**

```ts
// lib/selection-walk.ts
export type SelectionLevel = "none" | "block" | "para" | "line" | "word" | "region";
export interface SelectionPath {
  blockId?: string;
  paraId?: number | null;
  lineId?: number;
  wordId?: [number, number];
  regionId?: string;   // set for a confirmed region
  proposalId?: string; // set for an undecided proposal
}

// stores/selection-store.ts
export function selectRegion(regionId: string): void;
export function selectProposal(proposalId: string): void;

// stores/rail-store.ts
export type RailTarget = "block" | "para" | "line" | "word" | "region";
```

**Rules:**

- `pathLevel` returns `"region"` when either `regionId` or `proposalId` is set, checked **before**
  the existing `wordId` check.
- `selectRegion` and `selectProposal` clear `selectedParagraphs`, `selectedLines` and
  `selectedWords`, exactly as `selectBlock` does at `selection-store.ts:99`, set `level: "region"`,
  and set a path carrying only the one id.
- `walkSibling` is a no-op at the region level, as it already is at block level. Region stepping is
  Task 5's `n` and `p`, not the sibling walker.
- Add `"region"` to `VALID_TARGETS` in `rail-store.ts`. A persisted value of `"region"` read by this
  code is valid; an unknown value still falls back to `"word"`, so older and newer builds cannot
  break each other.
- `useRailHotkeys` maps `"5"` to `"region"`. Look at how keys `2` to `4` also sync
  `uiPrefs.selectionMode`, and leave `5` out of that sync the same way key `1` is.
- `RightPanel.tsx`'s `LEVEL_PLACEHOLDER` is an exhaustive `Record<SelectionLevel, string>`. Add
  `region: "Select a region"`. Route `level === "region"` to a placeholder `<div>` for now; Task 4
  replaces it with `RegionDetail`.
- `Breadcrumb.tsx`'s `renderChips` shows one chip, `Region` for a `regionId` and `Proposal` for a
  `proposalId`.

- [x] **Step 1: Write the failing tests.** Extend `src/stores/selection-store.test.ts`: `selectRegion`
  sets level `region`, path `{ regionId }`, and clears all three selected arrays; `selectProposal`
  likewise with `{ proposalId }`; `pathLevel({ proposalId: "p" })` is `"region"`. Extend the rail
  store and rail hotkey tests: pressing `5` sets target `region`; a persisted `"region"` is read back.
  Extend the Breadcrumb test for both chips.
- [x] **Step 2: Run them and see them fail** for the stated reason.
- [x] **Step 3: Implement.**
- [x] **Step 4: Run the focused tests, then typecheck.** The typecheck is where a missed exhaustive
  switch on `SelectionLevel` surfaces; find every consumer, not only the ones named here.
- [x] **Step 5: Run the whole Vitest suite, lint and format check, and commit**
  `feat(frontend): add the region rail target and selection level`.

> **Shipped 2026-09-17** in `feature/region-review` `78641a5`, with the Vitest suite at 1654 passed.
> **Two consumers this task did not name had to change.** `components/shell/Rail.tsx` holds four
> exhaustive `Record<RailTarget, string>` maps, and `lib/bbox-select.ts`'s `targetToLayerKey` is a
> `switch` over `RailTarget` with no default; neither compiles once `RailTarget` grows. A drag under
> the region target falls back to selecting words, matching `box-select-handler.ts`. **One gap was
> left for Task 2:** key `5` sets the target, but the rail shows no region cell, so nothing on screen
> says the target is active.

---

### Task 2: Click a region on the canvas

> **Shipped 2026-09-17** in `e7e4fd6`. 1673 Vitest tests; includes the visible rail region cell.

**Files:** new `src/lib/region-hit-test.ts` and `src/lib/region-hit-test.test.ts`;
`src/components/PageImageCanvas.tsx` and `PageImageCanvas.test.tsx`; `src/components/shell/Rail.tsx`
and its test.

**Show the region target in the rail.** Task 1 made key `5` select the region target but added no
visible cell, so a person cannot tell a click will now select regions. Add a region target cell
beside the block, paragraph, line and word cells, following their existing `TargetCell` pattern,
with the `5` hotkey hint. Colour it with the confirmed-region amber the canvas already uses in
`BBoxOverlay.tsx`'s `LAYER_COLORS`, so the cell and the shapes it selects match. Test that clicking
the cell sets the target and that the cell reads as active when the target is `region`.

**Interfaces — Consumes:** Task 1's `selectRegion`, `selectProposal`, `RailTarget`.
**Produces:**

```ts
// lib/region-hit-test.ts
import type { components } from "../api/types";
type RegionView = components["schemas"]["RegionView"];
type BBox = components["schemas"]["BBox"];

export interface RegionCandidate {
  kind: "region" | "proposal";
  id: string;   // region_id for kind "region", proposal_id for kind "proposal"
  box: BBox;    // in the same coordinate space the caller hit-tests in
  area: number;
}

export function regionCandidates(
  regions: readonly RegionView[],
  toBox: (box: BBox) => BBox,
): RegionCandidate[];

export function hitTestRegions(
  candidates: readonly RegionCandidate[],
  x: number,
  y: number,
): RegionCandidate | null;

export function orderedUndecidedProposals(regions: readonly RegionView[]): string[];
```

**Rules:**

- **Know which kind was hit.** A canvas item's id is `region_id ?? proposal_id`, so the existing
  item list cannot tell a confirmed region from a proposal. `regionCandidates` keeps the kind: a
  `RegionView` with `confirmed === true` and a `region_id` becomes kind `region`; one with
  `confirmed === false` and a `proposal_id` becomes kind `proposal`; anything else is dropped.
- **`toBox` is the coordinate transform.** `PageImageCanvas` already converts region boxes with
  `encoded ? rectToDisplay(r.box, encoded) : r.box` at about line 458. Pass that same conversion so
  the hit-test and the drawn rects agree.
- **`hitTestRegions` returns the smallest candidate containing the point**, edges inclusive. On
  exactly equal area it prefers kind `proposal`. With no candidate it returns `null`.
- **`orderedUndecidedProposals`** returns the `proposal_id` of every unconfirmed region, sorted by
  `box.y` ascending, then `box.x` ascending. It works in page coordinates, not display coordinates,
  since order does not depend on zoom.
- **In `PageImageCanvas`**, add a `railTarget === "region"` branch to the trivial-click hit-test at
  about line 580. Build candidates with `useMemo` next to `regionOverlayItems`. On a hit call
  `selectRegion` or `selectProposal`, then open the right panel the way the other branches do.
- **Draw the selected region.** When `level === "region"`, draw one highlight rect around the
  selected region or proposal, as a third `BBoxOverlay` layer `regions-selected`. Give it a stronger
  stroke than both existing region layers in `LAYER_COLORS`, and let it follow `layerVisibility.block`
  as the other two do.

- [x] **Step 1: Write the failing pure tests** in `region-hit-test.test.ts`, each with a hand-built
  `RegionView[]`:
  - a click inside a large confirmed region and a small proposal inside it hits the proposal;
  - a click inside two nested confirmed regions hits the inner one;
  - equal-area region and proposal at the same box: the proposal wins;
  - a click outside everything returns `null`;
  - a confirmed `RegionView` with no `region_id` is dropped from candidates;
  - `orderedUndecidedProposals` orders three proposals by `y` then `x` and skips confirmed regions.
- [x] **Step 2: Run them and see them fail.**
- [x] **Step 3: Implement `region-hit-test.ts`.** Run the pure tests to green.
- [x] **Step 4: Write the failing canvas test** in `PageImageCanvas.test.tsx`, following its existing
  mocked `@pdomain/pdomain-ui/canvas` and `image-event-surface` pattern: with the rail target
  `region`, a click at a proposal's centre sets the selection level `region` with that
  `proposalId`; with the rail target `word`, the same click does not select the proposal; the
  `bbox-overlay-regions-selected` sidecar's `data-item-count` is `1` after the click.
- [x] **Step 5: Implement the canvas changes.** Run the canvas tests, the whole suite, typecheck,
  lint, format, and commit `feat(frontend): select regions and proposals on the canvas`.

---

### Task 3: The mutation and run hooks

> **Shipped 2026-09-17** in `820cece`. 1664 Vitest tests on its branch; knip reports no unused exports.

**Files:** new `src/hooks/useRegionMutations.ts`, `src/hooks/useRegionMutations.test.tsx`,
`src/hooks/useProposalRuns.ts`, `src/hooks/useProposalRuns.test.tsx`; `src/test/handlers.ts`.

**Interfaces — Produces:**

```ts
type RegionRole = components["schemas"]["RegionRole"];

export function useAcceptProposal(projectId: string, pageIndex: number):
  UseMutationResult<PagePayload, Error, { proposalId: string; role?: RegionRole }>;
export function useRejectProposal(projectId: string, pageIndex: number):
  UseMutationResult<PagePayload, Error, { proposalId: string }>;
export function useEditRegion(projectId: string, pageIndex: number):
  UseMutationResult<PagePayload, Error, { regionId: string; role: RegionRole }>;
export function useDeleteRegion(projectId: string, pageIndex: number):
  UseMutationResult<PagePayload, Error, { regionId: string }>;

export function useProposePageKinds(projectId: string):
  UseMutationResult<{ job_id: string }, Error, void>;
export function useProposeRegions(projectId: string):
  UseMutationResult<{ job_id: string }, Error, void>;
```

**Routes, verified against the backend routers:**

| hook | method and path |
| --- | --- |
| `useAcceptProposal` | `POST /api/projects/{projectId}/pages/{pageIndex}/regions/proposals/{proposalId}/accept`, body `{}` or `{ role }` |
| `useRejectProposal` | `POST /api/projects/{projectId}/pages/{pageIndex}/regions/proposals/{proposalId}/reject` |
| `useEditRegion` | `PATCH /api/projects/{projectId}/pages/{pageIndex}/regions/{regionId}`, body `{ role }` |
| `useDeleteRegion` | `DELETE /api/projects/{projectId}/pages/{pageIndex}/regions/{regionId}` |
| `useProposePageKinds` | `POST /api/projects/{projectId}/propose-page-kinds`, returns `202 { job_id }` |
| `useProposeRegions` | `POST /api/projects/{projectId}/regions/propose`, body `{}`, returns `202 { job_id }` |

**Rules:**

- Copy the shape of `hooks/useLineMutations.ts`: a file-local request helper, a plain
  `useMutation`, and `onSuccess` invalidating `["page", projectId, pageIndex]`. That file's helper
  only POSTs; this file needs PATCH and DELETE too, so its helper takes the method.
- Accept sends `{}` when no role is given and `{ role }` when one is. Never send `role: undefined`
  as a key; the backend records `edited` when an override is present.
- The two run hooks do not invalidate anything themselves. Task 6's completion handler invalidates
  when the job finishes.
- Add MSW handlers for all six routes to `src/test/handlers.ts`, returning a minimal valid
  `PagePayload` or `{ job_id: "job-1" }`.

- [x] **Step 1: Write the failing hook tests**, following `hooks/useLineMutations.test.tsx` with
  `renderHook` and a `QueryClientProvider` wrapper. For each mutation hook, assert the method, the
  path, the body, and that `["page", projectId, pageIndex]` is invalidated on success. Assert the
  accept body is exactly `{}` with no role and exactly `{ role: "page number" }` with one.
- [x] **Step 2: Run and see them fail.**
- [x] **Step 3: Implement both hook files and the MSW handlers.**
- [x] **Step 4: Run the focused tests, the whole suite, typecheck, lint, format, and commit**
  `feat(frontend): add region mutation and proposal-run hooks`.

---

### Task 4: The region detail panel

> **Shipped 2026-09-17** in `c8d28d9`. 1694 Vitest tests after merge.

**Files:** new `src/components/right-panel/RegionDetail.tsx` and `RegionDetail.test.tsx`;
`src/components/shell/RightPanel.tsx`.

**Interfaces — Consumes:** Task 1's selection level and path; Task 3's four mutation hooks.
**Produces:** `export function RegionDetail(props: { page: PagePayload; projectId: string;
pageIndex: number }): JSX.Element`, the same prop shape every other detail panel takes.

**What it shows.** Look the selection up in the page payload: a `regionId` in `page.regions` where
`confirmed`, or a `proposalId` in `page.regions` where not confirmed, with its evidence and
disposition from `page.proposals`.

- **Proposal:** role, confidence to two decimals, a "Stale" badge when `stale` is true, and the
  evidence as a key and value list with values rendered by `JSON.stringify` for anything that is not
  a string or number. Three actions: **Accept**; **Accept as** a role picker listing every member of
  `RegionRole`; **Reject**.
- **Confirmed region:** role, and its origin, which is "From a proposal" when `proposal_id` is set
  and "Drawn by hand" otherwise. Two actions: **Change role**, a role picker that calls
  `useEditRegion`; **Delete**, which opens the existing confirm dialog through
  `dialogStore.openConfirm` and calls `useDeleteRegion` only on confirm.
- **Not found:** when the id is in neither list, which happens right after a decision removes a
  proposal, render a short "This region is no longer on the page" message and nothing else.
- Buttons are disabled while their mutation `isPending`. A failed mutation shows an inline message
  the way `LineDetail.tsx` does around line 379.

**The role list.** Build it from the `RegionRole` type, not from `BlockDetail.tsx`'s local layout
list, which is different. Use an exhaustive record, the idiom `RightPanel.tsx`'s `LEVEL_PLACEHOLDER`
and `Rail.tsx`'s target maps already use; the compiler rejects it if any `RegionRole` member is
missing:

```ts
const REGION_ROLE_RECORD: Record<RegionRole, true> = {
  paragraph: true, sidenote: true, "page header": true, /* ...every member... */ unknown: true,
};
// Object.keys always widens to string[]; the record above already proved completeness.
const REGION_ROLES = Object.keys(REGION_ROLE_RECORD) as RegionRole[];
```

> **Correction, found in execution.** This plan first gave a `satisfies` array plus a standalone
> `_allRolesListed` constant. It compiles under `tsc --noEmit`, and I had checked it that way, but the
> pre-commit hook runs `tsc -b --noEmit` with `noUnusedLocals` from `tsconfig.app.json`, which
> rejects the unused constant. ESLint ignores `_`-prefixed names; the TypeScript compiler does not.
> Verify compile-time claims with the command the hook runs, not a looser one.

In `RightPanel.tsx`, replace Task 1's placeholder with `RegionDetail`.

- [x] **Step 1: Write the failing panel tests**, following `right-panel/LineDetail.test.tsx`: a
  `PagePayload` literal, a `QueryClientProvider` with retries off, the selection driven through
  `selectProposal` and `selectRegion`, and MSW for HTTP. Cover: a selected proposal shows its role,
  confidence and evidence keys; clicking Accept POSTs to the accept route with `{}`; choosing a role
  in Accept as POSTs `{ role }`; Reject POSTs to reject; a selected confirmed region shows its origin;
  Delete does not call the route until the confirm dialog is confirmed; an id in neither list shows
  the not-found message; a stale proposal shows the badge.
- [x] **Step 2: Run and see them fail.**
- [x] **Step 3: Implement the panel and the `RightPanel` routing.**
- [x] **Step 4: Run the focused tests, the whole suite, typecheck, lint, format, and commit**
  `feat(frontend): add the region detail panel`.

---

### Task 5: Review from the keyboard

**Files:** new `src/hooks/useRegionReviewHotkeys.ts` and its test; `src/lib/hotkeyMap.ts`; the
component that mounts page-level hotkeys, `src/pages/ProjectPage.tsx`, near the existing
`useMatchesHotkeys` call.

**Interfaces — Consumes:** Task 1's rail target, level and path; Task 2's
`orderedUndecidedProposals`; Task 3's `useAcceptProposal`, `useRejectProposal`, `useDeleteRegion`.
**Produces:** `export function useRegionReviewHotkeys(args: { page: PagePayload | undefined;
projectId: string; pageIndex: number }): void`.

**Keys, all registered through `useHotkey` so they respect its form-field and open-dialog guards:**

| key | enabled when | does |
| --- | --- | --- |
| `n` | rail target is `region` | select the next undecided proposal after the current one, wrapping to the first |
| `p` | rail target is `region` | select the previous one, wrapping to the last |
| `enter` | a proposal is selected | accept it with no role override |
| `x` | a proposal is selected | reject it |
| `delete` | a confirmed region is selected | open the confirm dialog, then delete |

**Auto-advance.** Before firing accept or reject, compute the proposal that follows the current one
in `orderedUndecidedProposals(page.regions)`. On the mutation's success, select it; if there is none,
call `clearSelection()` and show `toast.info("No undecided proposals left on this page")`. Compute
the next one before the mutation, because the refetched page no longer contains the decided
proposal.

**`n` with nothing selected** selects the first undecided proposal. With none on the page it shows
the same toast.

Register `5`, `n`, `p`, `enter`, `x` and `delete` in `HOTKEY_MAP` under a new `"region-review"`
scope so the help modal lists them. Check `hotkey-registry.ts` for how a new scope is named and
displayed.

- [x] **Step 1: Write the failing hook tests.** Render the hook with a page carrying three proposals
  at known `y` and `x`, set the rail target to `region`, and dispatch key events. Cover: `n` from
  nothing selects the topmost; `n` twice selects the second; `p` from the first wraps to the last;
  `enter` POSTs accept for the selected proposal and then selects the next one in order; `x` on the
  last one POSTs reject, clears selection and shows the toast; `n`, `enter` and `x` do nothing when
  the rail target is not `region`; `delete` on a confirmed region does not call the route before the
  dialog is confirmed.
- [x] **Step 2: Add a regression test for the collision the design found.** With the rail target
  `region`, pressing `n` must leave `worklistStore`'s `selectedLineIndex` unchanged. This is the test
  that fails if someone later rebinds review to `j` and `k`.
- [x] **Step 3: Run and see them fail.**
- [x] **Step 4: Implement, mount the hook in `ProjectPage.tsx`, register the keys.**
- [x] **Step 5: Run the focused tests, the whole suite, typecheck, lint, format, and commit**
  `feat(frontend): review proposals from the keyboard`.

---

### Task 6: Start the runs, and make an empty run say why

Two halves, one commit each. Do the backend half first.

> **Backend half shipped 2026-09-17** in `99f71a2` and `6589231`. `pages_detected` counts pages
> that received at least one proposal. Lease failures, missing measurements and detector errors
> are named in a separate clause when non-zero, because clicking Propose page kinds fixes none of
> them.
>
> **Correction for the frontend half, found before dispatch.** `useJobCompletionInvalidation`'s
> `onComplete` receives only the job id, so it cannot show the terminal message. It is extended to
> receive the terminal event, as `onRunning` already does. And its `invalidationKey` is required, so
> both runs invalidate the page query rather than Propose page kinds invalidating nothing.

**Backend half — `core/jobs/handlers/propose_regions.py`.** The run skips every page with no proposed
or confirmed page kind and says so only in a server log. Make its **last** `runner.update_progress`
call a summary. The runner's completion step changes only `status` and `completed_at`, so this
message is what the terminal SSE frame carries; that was verified in `core/jobs/runner.py`.

The summary reads:

- `Proposed {proposal_count} region(s) on {pages_detected} page(s).` always;
- then, separated by one space, `Skipped {n} page(s) with no page kind; run Propose page kinds
  first.` when any were skipped for that reason;
- and the existing "No page has a proposed or confirmed page kind" early-return message gains the
  same hint.

Test in `tests/unit/core/jobs/test_propose_regions_handler.py`: a run with one page confirmed and one
page with no kind state ends with a progress message containing `Skipped 1 page(s)` and
`Propose page kinds`. Confirm it fails first. Keep progress monotonic against the combined total; an
existing test pins that. Commit `feat(regions): end a proposal run with a summary message`.

**Frontend half — `src/components/PageActionsCompact.tsx`.** Add **Propose page kinds** and
**Propose regions** actions. Copy the auto-rotate-all pattern in that file exactly: the mutation
stores the returned job id and opens a loading toast keyed by it; `useJobCompletionInvalidation`
drives the rest. On completion:

- **Propose regions** invalidates `["page", projectId, pageIndex]` and shows the job's terminal
  `message` in the success toast, not a generic "complete".
- **Propose page kinds** shows its terminal message too. It invalidates nothing, since no page view
  shows a proposed kind yet.

Test in `PageActionsCompact.test.tsx`, following its existing auto-rotate tests: clicking Propose
regions POSTs to the route, and a completed job event whose `message` is
`"Proposed 0 region(s) on 0 page(s). Skipped 3 page(s) with no page kind; run Propose page kinds
first."` produces a success toast containing that text. Commit
`feat(frontend): start proposal runs from the page actions`.

---

### Task 7: The whole loop in a browser

**Files:** new `tests/e2e/test_region_review_loop.py`, at the repo root, in Python.

Copy the self-contained fixture server from `tests/e2e/test_region_layer_visibility.py`: it seeds a
page, appends a proposal through `RegionProposalLog`, boots its own uvicorn and loads the project.
Seed **two** proposals on the page, one above the other.

The test:

1. Open the page. Press `5`.
2. Press `n`. Assert through the API that nothing has changed yet, and that the right panel shows
   the top proposal's role.
3. Press `enter`. Poll `GET /api/projects/{id}/pages/0` until its `regions` contain exactly one
   confirmed region and one unconfirmed proposal.
4. Press `x`. Poll until `regions` contain exactly one confirmed region and no proposal, and assert
   the reject was recorded by reading the decision log the fixture exposes.

Run with `make AI=1 e2e`, which builds the SPA first. If Chromium is not installed, stop and report;
do not install it without saying so. Commit `test(e2e): review region proposals from the keyboard`.

---

## What this plan does not do

- Draw a new region, resize a box, or edit word membership. The routes exist; the design defers
  them.
- Review page kinds. The payload carries the confirmed kind, not the proposed one.
- Jump to the next page with undecided proposals, or rank proposals across the book. That is
  slice 5.
- Style stale proposals differently on the canvas. The panel flags them.
- Wire `BlockDetail`'s "model suggests" callout, or replace its local layout list with `RegionRole`.

## Related

- [Region review surface design](../specs/2026-09-17-region-review-surface-design.md) — the design
  this carries out.
- [Geometry region proposals](2026-09-17-geometry-region-proposals.md) — slice 4, which produces the
  proposals this reviews.
- [Region routes and proposal run](2026-09-08-region-routes-and-proposal-run.md) — the routes and the
  canvas region layer this builds on.
