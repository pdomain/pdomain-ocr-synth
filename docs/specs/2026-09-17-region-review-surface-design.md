---
Status: active
Owner: CT
Created: 2026-09-17
Last verified: 2026-09-17
Kind: spec
---

# The first review surface is a keyboard loop over proposals, not a region editor

## Agent Index

- **Kind:** spec
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-17
- **Last verified:** 2026-09-17
- **Provenance:** authored 2026-09-17 from a read-only survey of `pdomain-ocr-labeler-spa/frontend/`
  (`PageImageCanvas.tsx`, `BBoxOverlay.tsx`, `shell/RightPanel.tsx`, `right-panel/BlockDetail.tsx`,
  `stores/selection-store.ts`, `stores/rail-store.ts`, `hooks/useRailHotkeys.ts`,
  `hooks/useLineMutations.ts`, `hooks/useJobProgress.ts`, `hooks/useJobCompletionInvalidation.ts`,
  `components/PageActionsCompact.tsx`, `lib/hotkeyMap.ts`), the backend request and view models in
  `api/regions.py` and `core/models.py`, and the furniture coverage measurement behind slice 4
- **Disposition:** Active. Slice 3 of the labeling track, first increment. Planned at
  `docs/plans/2026-09-17-region-review-surface.md`.
- **Read when:** building any region or proposal UI in the labeler, adding a rail target, or
  adding review keyboard shortcuts.
- **Search terms:** slice 3, region review, proposal review, RegionDetail, rail target region,
  accept proposal, reject proposal, review hotkeys, propose regions button.

## What this settles

The first region surface lets a person work through a page's proposals from the keyboard. For each
one, they accept it, accept it with a different role, or reject it. Drawing new regions, resizing
boxes and editing word membership come later.

That order follows from what the labeler now produces. Slice 4 proposes page furniture. The five
aligned corpus books carry a furniture band on 1,089 of their 1,385 pages. At one or two regions per
band, that is on the order of 400 proposals per book, waiting for a yes or a no. The job worth
building first is the one that turns those into confirmed ground truth quickly.

## Today a person can see a region and cannot touch it

The backend is complete and the frontend reaches none of it.

- **Regions render but do not respond.** `PageImageCanvas` draws confirmed regions and proposals as
  two `BBoxOverlay` layers, amber and sky blue. The rects are built with `listening: false`. The
  click hit-test checks blocks, paragraphs, lines and words only.
- **No client code calls a region or page-kind route.** All ten routes exist in the generated
  `types.ts` and nowhere else. The MSW test handlers have none of them.
- **Most of what the payload carries about a region is never read.** `PagePayload.proposals`, with
  each proposal's evidence and disposition, is unused. So are `role`, `confidence` and `stale` on
  every `RegionView`.
- **Nothing starts a proposal run from the UI.** Neither `propose-page-kinds` nor `regions/propose`
  has a button.

## Regions become a fifth rail target

Selection in the labeler is scoped by the rail's target: block, paragraph, line or word, on keys
`1` to `4`. The target decides which layer a click hit-tests against. A region is a fifth kind of
thing to select, so it gets a fifth target, `region`, on key `5`.

This keeps one rule for every click on the canvas. A region overlaps the words inside it by
definition. A proposal can also overlap a confirmed region. Letting a click hit several layers at
once would need an ordering nobody has designed. With `region` as the target, a click hit-tests
confirmed regions and proposals only.

**When several regions contain the click, the smallest wins.** Two cases make this necessary.
Regions nest by design: a click inside a child region is also inside its container, and the child is
what the person is pointing at. A proposal from a newer run can also overlap a region someone already
confirmed with a different box.

An accepted proposal is not one of these cases. The resolver drops a proposal from
`PagePayload.regions` once its decision carries a `region_id`, so a proposal and the region made from
it never appear together. When two candidates have exactly equal area, the undecided proposal wins,
since it is the one still waiting for a decision.

**The rail's existing `region` mode is a different thing and stays as it is.** It is labelled
"Refine" and maps to plain selection. The name collision is unfortunate and is not this design's to
fix.

## A selected region gets its own panel

`RightPanel` chooses a detail panel from the selection store's level. Add a `region` level, whose
path carries either a `regionId` for a confirmed region or a `proposalId` for a proposal. Add a
`RegionDetail` panel beside `BlockDetail`.

For a **proposal**, the panel shows the role, the confidence, whether it is stale, and the evidence
as a plain key and value list. It offers three actions:

- **Accept**, which calls the accept route with no overrides and records the disposition
  `accepted`.
- **Accept as another role**, a role picker populated from the generated `RegionRole` union, which
  calls the accept route with `role` set and records the disposition `edited`.
- **Reject**, which records a verified negative. Nothing on the page changes.

For a **confirmed region**, the panel shows the role and where it came from, and offers:

- **Change role**, through the edit route.
- **Delete**, through the delete route, behind the existing confirm dialog.

**The evidence is shown raw, and that is deliberate.** Slice 4's evidence names the band, the
cluster width, the text width, the gap threshold and whether that threshold was fitted or a
fallback, and the page's classification confidence. A reviewer deciding whether a header is really a
header needs exactly those numbers. A formatted summary would have to choose which to hide.

## Review runs from the keyboard, and advances by itself

Four hundred decisions a book is only tolerable if each one takes a keystroke.

| key | does | when |
| --- | --- | --- |
| `5` | select the region target | always, alongside `1` to `4` |
| `n` | select the next undecided proposal on the page | region target |
| `p` | select the previous undecided proposal | region target |
| `enter` | accept the selected proposal | a proposal is selected |
| `x` | reject the selected proposal | a proposal is selected |
| `delete` | delete the selected confirmed region, with confirm | a confirmed region is selected |

**After an accept or a reject, selection moves to the next undecided proposal.** When the page has
none left, selection clears and a toast says so. Moving to the next page stays manual, because
finding the next page with undecided proposals is a book-level query no route answers yet.

**Proposals are ordered top to bottom, then left to right.** That puts a running head before its
folio and matches the order a person reads the page in.

**These keys avoid every key already bound while a person works the page.** Two listeners are
always on, with no gate on focus or rail target:

- `useRailHotkeys` is a raw `document` listener firing on `1` to `4`, `v`, `r`, `a` and `e` whenever
  no input has focus.
- `useMatchesHotkeys` is registered unconditionally at page level in `ProjectPage.tsx`. It binds `j`
  and `k` to the matches worklist's next and previous line, and `v`, `u`, `d`, `o`, `g`, `m` and `r`
  to line actions.

So `j` and `k`, the obvious next and previous keys, are taken. Using them would also move the
matches worklist cursor on every step through proposals. `n` and `p` are free.

Each new key must be added to `HOTKEY_MAP` by hand, or the help modal will not show it.

## Two book actions start the runs

`PageActionsCompact` already starts book-scoped jobs, such as auto-rotate-all, with a loading toast
that the job's progress updates. Add two actions following exactly that pattern:

1. **Propose page kinds**, which must run first. A region run skips any page whose kind was never
   proposed or confirmed.
2. **Propose regions**, which invalidates the page query when the job completes, so new proposals
   appear on the current page without a reload.

Both are background jobs over the whole book, so neither blocks the page.

**A region run that produced nothing must say why.** `handle_propose_regions` skips every page with
no proposed or confirmed kind and records that only in a server log. A person who clicks Propose
regions before Propose page kinds would get a success toast and an unchanged page.

The handler's last progress update should therefore summarize the run: how many proposals, on how
many pages, and how many pages were skipped for having no page kind. It should also hint to run
Propose page kinds first when any pages were skipped.

The completion toast shows that terminal message rather than a generic "complete". The job's
terminal SSE frame already carries `message`, and `useJobProgress` already normalizes it.

## What changes, file by file

| file | change |
| --- | --- |
| `stores/rail-store.ts` | add `region` to `RailTarget` and its valid set |
| `hooks/useRailHotkeys.ts` | map `5` to the region target |
| `stores/selection-store.ts`, `lib/selection-walk.ts` | add a `region` level and `regionId` / `proposalId` path fields |
| `components/PageImageCanvas.tsx` | hit-test regions and proposals under the region target, smallest first; draw a highlight for the selected region |
| `hooks/useRegionMutations.ts` | new: accept, reject, edit, delete, each invalidating the page query the way `useLineMutations` does |
| `hooks/useProposalRuns.ts` | new: start the page-kind and region runs, returning the job id |
| `components/right-panel/RegionDetail.tsx` | new: the panel above |
| `components/shell/RightPanel.tsx` | route the `region` level to `RegionDetail`, and add a `region` entry to `LEVEL_PLACEHOLDER`, which is an exhaustive `Record<SelectionLevel, string>` and will not compile without one |
| `components/shell/Breadcrumb.tsx` | show a region or proposal chip; `renderChips` branches on the path's block, paragraph, line and word ids and would otherwise render nothing |
| `hooks/useRegionReviewHotkeys.ts` | new: `n`, `p`, `enter`, `x`, `delete` under the region target |
| `lib/hotkeyMap.ts` | register the new keys |
| `components/PageActionsCompact.tsx` | the two book actions, showing each run's terminal message on completion |
| backend `core/jobs/handlers/propose_regions.py` | end the run with a summary progress message naming proposals, pages, and pages skipped for no page kind |

One small backend change is needed: the region run's final progress message, described above. Every
route, request model and view this surface uses already exists.

## Follow the patterns already in the codebase, including the imperfect ones

**Mutations invalidate rather than write the cache.** Each accept, reject, edit and delete route
returns the full `PagePayload`, and it would be faster to write that straight into the query cache.
Every other mutation in the labeler invalidates `["page", projectId, pageIndex]` instead. A second
convention in one screen is worse than a slightly slower refetch. Change both together or neither.

**Each hook file keeps its own small `apiPost` helper.** There is a generic `ApiClient` that nothing
uses, and three hook files each copy a helper. Adding a fourth copy is consistent with what exists;
consolidating them is a separate cleanup.

## What this increment does not build

- **Drawing a region.** `create_region` has a route and no UI. It needs a drag interaction on the
  canvas that does not conflict with box-select, which is its own design question.
- **Resizing a box or editing word membership.** Both routes exist. Neither is needed to decide
  a proposal.
- **Reviewing page kinds.** The payload carries the confirmed kind but not the proposed one, so a
  page-kind review panel needs a backend change first.
- **A book-wide review queue.** Jumping to the next page with undecided work, and ranking proposals
  by confidence across the book, are slice 5.
- **Stale styling on the canvas.** A stale proposal is flagged in the panel. Drawing it differently
  would need a dash or pattern option `BBoxOverlay` does not have.

## Two inconsistencies this design notices and leaves alone

**`BlockDetail` has a "model suggests" callout wired to nothing.** Its suggestion is hard-coded to
null with a comment saying the backend is not wired yet. Proposals are now the backend it was
waiting for. But a block is not a region. Whether that callout should show a containing proposal is
a separate question.

**`BlockDetail` keeps its own local list of layout types** rather than the backend's `RegionRole`
enum. `RegionDetail` must use `RegionRole` from the generated types, so the two panels will offer
different role lists until `BlockDetail` is changed.

## Related

- [Geometry region proposals](2026-09-17-geometry-region-proposals-design.md) — slice 4, which
  produces what this surface reviews.
- [Region provenance and persistence](2026-09-07-region-provenance-and-persistence-design.md) — the
  accept, edit and reject dispositions this surface records.
- [Region routes and proposal run](../plans/2026-09-08-region-routes-and-proposal-run.md) — the
  routes this surface calls, and the canvas region layer it makes clickable.
- [Labeling track roadmap](../plans/2026-09-07-labeling-track-roadmap.md) — where slice 3 sits.
