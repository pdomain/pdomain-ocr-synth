---
Status: draft
Owner: CT
Created: 2026-09-17
Last verified: 2026-09-17
Kind: spec
---

# A person reviewing a book should never have to hunt for the next proposal

## Agent Index

- **Kind:** spec
- **Status:** draft
- **Owner:** CT
- **Created:** 2026-09-17
- **Last verified:** 2026-09-17
- **Provenance:** authored 2026-09-17 from the shipped region review surface and a run of the region
  pipeline on real OCR'd books, and from direct inspection of `pdomain-ocr-labeler-spa`
  `core/regions/proposal_log.py`, `core/regions/decision_log.py`, `core/regions/resolver.py`,
  `api/pages.py`, `frontend/src/pages/ProjectPage.tsx`, `frontend/src/hooks/useRegionReviewHotkeys.ts`
  and `frontend/src/lib/hotkeyMap.ts`
- **Disposition:** Draft. First increment of slice 5 of the labeling track, plus the decision
  carry-forward the owner ruled on 2026-09-08 and nothing had built.
- **Read when:** building book-level review navigation, the review queue route, or anything that
  answers "what should a person or an agent look at next".
- **Search terms:** slice 5, review queue, undecided proposals, next page with work, review-queue
  route, bracket keys, confidence ranking, agent affordance, carried decision, carry-forward.

## What this settles

The labeler should answer one question for the whole book: which proposals are still undecided,
and in what order. A person uses the answer to jump to the next page with work on it. An agent uses
the same answer, from the same route, to decide what to review next.

Today a person can decide every proposal on a page from the keyboard, then must page through the
book by hand to find the next one. On a real book that is most of the effort. Across 30 real pages of
each of three corpus books, 20 to 23 pages carried a head and folio pair, so a book of a few hundred
pages holds several hundred proposals spread over most of its pages.

## Decisions must carry across runs first, or the queue fills with work already done

**Every re-run of `propose_regions` re-proposes what a person already decided.** Proposal ids are
minted fresh per run. Nothing matches a new proposal to a region already confirmed, so the page view
and any queue show it as undecided work again. The owner ruled on this on 2026-09-08, in the
[provenance design](2026-09-07-region-provenance-and-persistence-design.md): a decision carries
across runs, recorded as its own `carried` disposition naming the run and proposal it came from.
`Disposition.CARRIED` and its two fields exist in `core/regions/models.py`, and nothing ever writes
one. This increment builds it, because without it the queue is wrong after the second run.

**The rule, from the ruling.** At the end of a region run, compare each new proposal with the
confirmed regions on its page. A new proposal matches a confirmed region when the two agree on role
and their boxes overlap with an intersection-over-union of at least 0.7. A match writes a decision
with disposition `carried`, `region_id` set to the confirmed region, and `carried_from_run_id` and
`carried_from_proposal_id` naming the decision that confirmed it. The 0.7 is a starting value, named
in code and uncalibrated.

**Exactly what a carried decision holds.** Decisions are looked up by the proposal being decided,
keyed by that proposal's own id and run id, the convention accept and reject already use. So:

| field | value |
| --- | --- |
| `proposal_id`, `run_id` | the **new** proposal's own id and run id |
| `disposition` | `carried` |
| `region_id` | the matched confirmed region |
| `carried_from_proposal_id`, `carried_from_run_id` | the proposal and run of the decision that **originally confirmed** the region |

Writing the origin's run id into `run_id` would make the lookup miss, and the carried proposal would
still show as undecided.

**Find the origin by disposition, not by region id alone.** Each confirmed region has exactly one
`accepted` or `edited` decision naming it, minted when a person confirmed it. Every later carry adds
another decision naming the same `region_id`. The origin lookup must filter to `accepted` and
`edited`, or on the second and later re-runs it would name a previous carry as the origin.

**Why the page view needs no new filtering.** The resolver already hides a proposal whose decision
has a `region_id`, so a carried proposal disappears by the rule that already hides accepted ones.

**Deleting a region must reject every proposal that decided it, not only the first.** Today
`delete_region` records a rejection for the one proposal stored on the region block as
`source_proposal_id`, so a deleted region's proposal comes back as reviewable work rather than
vanishing silently. Once carries exist, several proposals' latest decisions can name that region.
Delete must record a rejection for every proposal whose latest decision names the deleted
`region_id`. Otherwise each carried proposal stays hidden forever behind a decision pointing at a
region that no longer exists.

**Two cases the ruling does not cover, left alone and named here.**

- **A hand-drawn region.** It has no originating run or proposal, and a carried decision must name
  both. A new proposal overlapping a hand-drawn region stays undecided. The owner should decide
  whether that is right.
- **A rejection.** The ruling carries a confirmed region, not a refusal. A new run proposing
  something a person rejected before will be proposed again. Carrying rejections would save review
  effort, but a better model re-proposing a region a worse one got wrong would inherit the old "no",
  so it is the owner's call.

**A carried decision is machine-written, and says so.** It is appended to the decision journal by
the job, never to the page blob. Its disposition keeps it out of any count of human agreement, as the
ruling requires.

## One route answers the question for people and agents alike

Add `GET /api/projects/{project_id}/regions/review-queue`. It always returns a count and a per-page
summary, whose size is bounded by the book's page count. It returns individual items only up to a
`limit`:

```json
{
  "total_undecided": 312,
  "pages": [
    {"page_index": 20, "undecided": 2, "first_proposal_id": "…", "last_proposal_id": "…"}
  ],
  "items": [
    {"page_index": 20, "proposal_id": "…", "run_id": "…", "role": "page header",
     "confidence": 0.6, "box": {"x": 353, "y": 112, "width": 396, "height": 30}}
  ]
}
```

**`limit` defaults to 0 and is capped at 500.** The UI never needs the items: `pages` alone answers
where the next page with work is and which proposal to select there. An agent asks for items, in
either order, a bounded page at a time.

**The queue and the page view must agree exactly on what is undecided, so they share one
predicate.** The resolver hides a proposal whose latest decision is `rejected` or names a
`region_id`, which covers accepted, edited and carried decisions. Extract that test from
`resolve_regions` into a function both the resolver and the queue call, rather than restating it.
Otherwise `]` can land on a page that shows nothing to review.

**Two orders, chosen by a query parameter.**

- `order=reading`, the default: by page index, then top to bottom, then left to right. This is the
  order a person works through a book.
- `order=confidence`: lowest confidence first, then reading order. This is the roadmap's ranking of
  work "so a person reviews what the model was unsure about", and what an agent triaging a book wants.
  A proposal with no confidence sorts first, because a missing score is the least certain of all.

`order` affects only `items`. `pages` is always in page order.

**The route reads the two journals once each, not once per page.** `RegionProposalLog` has only a
per-page accessor today, and calling it for every page of a book re-parses the whole journal each
time. Add a public `proposals()` accessor that reads the journal once.

**Staleness is left out of the queue.** A proposal goes stale when a facet it was computed from has
changed on its page, and computing that needs the page loaded. The queue does not load every page
to answer a navigation question. A stale proposal is still undecided work, and the page view still
flags it when a person opens the page.

## Two keys move between pages that have work

| key | does |
| --- | --- |
| `]` | go to the next page after this one with an undecided proposal, and select its first |
| `[` | go to the previous such page, and select its last |

**Both keys are free.** `shift+n` was the obvious choice but its pair `shift+p` toggles the
paragraphs layer in the viewport scope. `useRailHotkeys` and `useMatchesHotkeys` bind neither bracket.

**They work under the region rail target only**, like `n`, `p`, `enter` and `x`, so a person cannot
jump pages by accident while editing words.

**Selecting after navigation needs an intent, not a direct call.** A page change clears a region
selection, and the new page's payload is not loaded at the moment the key fires. So the key records
which proposal to select and navigates; once the new page's payload arrives and contains that
proposal, the selection is made and the intent cleared. If the proposal is not on the loaded page,
for example because a refetch removed it, the intent is dropped without selecting anything.

**At the end of a page, say where the work is.** Deciding the last undecided proposal on a page
clears the selection and shows "No undecided proposals left on this page" today. Extend it: when the
book has more, say how many and name the key, for example "No undecided proposals left on this page.
12 left in the book; press ] for the next". Do not navigate automatically. Moving the page out from
under someone who is still looking at it is disorienting.

## A count stays visible

The rail's region target cell shows the book's undecided count as a small badge, so a person always
knows how much is left. The count comes from the same query, called with `limit=0` so it carries only
the count and the page summary, and refreshes when a decision lands or a proposal run completes. A
refetch after every keyboard decision is cheap at that size.

## What changes, file by file

| file | change |
| --- | --- |
| backend `core/regions/proposal_log.py` | public `proposals()` bulk accessor |
| backend `core/regions/resolver.py` | extract the undecided predicate so the queue shares it |
| backend `core/jobs/handlers/propose_regions.py` | write `carried` decisions for proposals matching a confirmed region |
| backend `api/regions.py` `delete_region` | reject every proposal whose latest decision names the deleted region |
| backend `api/regions.py` | `GET .../regions/review-queue` with `order` and `limit` |
| `frontend/src/hooks/useReviewQueue.ts` | new: the query, keyed `["review-queue", projectId, order, limit]`, invalidated by the `["review-queue", projectId]` prefix |
| `frontend/src/hooks/useRegionMutations.ts` | also invalidate the review queue on every decision |
| `frontend/src/components/PageActionsCompact.tsx` | invalidate the review queue when a proposal run completes |
| `frontend/src/hooks/useRegionReviewHotkeys.ts` | `[` and `]`, the selection intent, the end-of-page message |
| `frontend/src/components/shell/Rail.tsx` | the undecided count badge on the region cell |
| `frontend/src/lib/hotkeyMap.ts` | register `[` and `]` |

## What this increment does not build

- **A queue panel listing every item.** The route supports one; the first increment only navigates.
- **Confidence-ordered navigation in the UI.** The route supports `order=confidence`; the keys use
  reading order, because jumping around the book by confidence is disorienting for a person. An
  agent can use the other order today.
- **Calibration.** The decisions this surface records are what will eventually calibrate the
  detector's confidence scores. Nothing here uses them yet.

## Related

- [Region review surface](2026-09-17-region-review-surface-design.md) — slice 3, whose page-level
  review this extends to the book.
- [Geometry region proposals](2026-09-17-geometry-region-proposals-design.md) — slice 4, which fills
  the queue.
- [Labeling track roadmap](../plans/2026-09-07-labeling-track-roadmap.md) — slice 5's goals.
