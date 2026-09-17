---
Status: draft
Owner: CT
Created: 2026-09-17
Last verified: 2026-09-17
Kind: spec
---

# A person can see and confirm every page's kind, one page or a whole book at a time

## Agent Index

- **Kind:** spec
- **Status:** draft
- **Owner:** CT
- **Created:** 2026-09-17
- **Last verified:** 2026-09-17
- **Provenance:** authored 2026-09-17 from direct inspection of `pdomain-ocr-labeler-spa` at
  master `3087aa0`: `api/pages.py` (`PagePayload`, `confirm_page_kind`, `ConfirmPageKindRequest`),
  `core/page_kind/models.py`, `core/page_kind/proposal_log.py`, `core/page_kind/reviewed_store.py`,
  `core/jobs/handlers/propose_page_kinds.py`, `core/jobs/handlers/propose_regions.py`,
  `core/page_state.py` (`ensure_page_model`), `api/history.py`, and the frontend `components/PageActionsCompact.tsx`,
  `components/right-panel/RegionDetail.tsx`, `components/drawer/Worklist.tsx`,
  `components/drawer/BulkActions.tsx`, `stores/dialog-store.ts`, `hooks/usePageMutations.ts`
- **Disposition:** Draft. Second increment of slice 5 of the labeling track, after the
  [book review queue](2026-09-17-book-review-queue-design.md).
- **Read when:** building page-kind review in the labeler, reading page-kind proposals over the API,
  or confirming page kinds for many pages at once.
- **Search terms:** page kind review, confirm page kind, bulk confirm, page kinds list, proposed
  kind, reviewed marker, page-kind confidence, slice 5.

## What's missing today, and what this design adds

A person cannot review page kinds today, because nothing shows them. `propose_page_kinds` writes a
proposal for every page, and `POST .../pages/{index}/page-kind` records a person's answer. But no
route returns a proposal, and no screen shows a page's kind, proposed or confirmed. The real-book
run in `/workspaces/pdomain/.m15f-evidence/real-book-region-run/` had to use the API directly.

This design adds three things:

- The page payload carries the page's latest kind proposal.
- One book route lists every page's proposed and confirmed kind, and one route confirms many pages
  at once.
- The SPA shows the kind on the page toolbar, lets a person confirm or change it there, and opens a
  book-wide list for bulk review.

Page kind is not a region, so none of the region decision machinery applies. A page has one kind. A
person's answer replaces the machine's outright, as the
[provenance design](2026-09-07-region-provenance-and-persistence-design.md) rules in "Page kind
needs a marker, not a decision log".

## Why a person must set most kinds by hand

**The classifier proposes only three kinds.** `_PAGE_CLASS_TO_KIND` in `propose_page_kinds.py` maps
the measured page class to `body`, `chapter opening`, or `unknown`. `PageKind` has fourteen values.
Title pages, contents, plates, blanks, indexes and the rest are never proposed, so a person must
choose them.

**Most of a book is body pages, so confirming must work in bulk.** Confirming a 300-page book one
page at a time is 300 separate actions for pages that nearly all say `body`. A person should select
the pages they have checked and confirm them in one action.

**Confirming kinds does not yet change region proposals.** `FurnitureDetector` reads the measured
page class from `DetectorInput.classification`, not the confirmed kind. `propose_regions` uses page
kind only to decide which pages are eligible: a page with a proposed or confirmed kind runs, and any
other page is skipped. Confirmed kinds matter now as ground truth for later layout training, and
later for detectors that condition on them.

## The page payload carries the latest proposal

`PagePayload` gains one field, `page_kind_proposal`, which is `null` when no run has proposed a kind
for the page:

| field | source |
|---|---|
| `proposal_id` | `PageKindProposal.proposal_id` |
| `run_id` | `PageKindProposal.run_id` |
| `kind` | `PageKind`, including `unknown` |
| `confidence` | `float` or `null`; `null` means the classifier declined, never a score of zero |
| `evidence` | the stored evidence mapping, today `page_class` and `template_residual_px` |

The value comes from `PageKindProposalLog.latest_proposal_for_page`. It is read best-effort, the way
`page_kind_reviewed` is read today: a failed read logs a warning and leaves the field `null` rather
than failing the page.

## A reviewed marker records the kind and how it was confirmed

`PageKindReviewedMarker` gains two optional fields:

- `kind`: the `PageKind` the page carries after the change.
- `method`: `single` for the page route, `bulk` for the book route, `history` for an undo or redo.

Old markers have neither field, and still read back correctly. The page blob stays the source of
truth for a page's kind.

The marker's copy of the kind exists for two reasons: so the book route can answer without loading
every page, and so a later calibration can tell a page a person looked at alone from a page
confirmed in a batch.

**An undo or redo that changes the kind writes a marker too.** Page history restores an earlier page
blob, which can carry an earlier kind. Without a marker, the journal would keep the kind the undo
removed. The live page would hide that only while it stays in memory.

A server restart unloads every page. `load_page` in `api/pages.py`, the handler behind
`POST .../pages/{index}/load`, drops one page's state on purpose too. After either event, the book
route would report a kind the page no longer has.

So `undo` and `redo` in `api/history.py` compare the page's kind before and after the change. When
it changed, they append a marker with `method: history` and the new kind. A history marker whose
kind is `null` withdraws the review: the undo took the page back to before anyone confirmed it.

Only a person's confirm ever sets `Page.page_kind`, so a blob without one really is unreviewed.
`PageKindReviewedStore.is_reviewed` and `reviewed_page_indices` must treat that page as unreviewed.
That also keeps `propose_regions`, which reads `reviewed_page_indices`, from counting a withdrawn
review.

The marker is appended after the page save succeeds, the order `confirm_page_kind` already uses. If
the append fails, the undo or redo still returns its result and logs a warning. The page change has
happened and must not be reported as failed. The book route still reports the right kind while the
page stays loaded.

**Re-OCR and rotation keep the confirmed kind.** Reload OCR, page rotation, and auto-rotate-all each
call `loader.run_ocr`, then `_apply_reocr_outcome`. Reload OCR lives in
`core/jobs/handlers/reload_ocr.py`, page rotation in `rotate.py`, and auto-rotate-all in
`auto_rotate_all.py`. `run_ocr` builds a fresh `Page` and saves it through `_ingest_ocr_result` in
`adapters/ocr/local_doctr.py`, under a new `page_id`.

A fresh page has no `page_kind`, so today all three silently drop a confirmed kind. A page's kind
describes the printed page, which none of these actions changes.

The kind must be on the page before that save, not added afterwards. `run_ocr` gains a keyword,
`page_kind`, which it sets on the fresh `Page` before `_ingest_ocr_result` writes it. Each caller
reads the prior kind from the page state before it runs OCR and passes it in. The page is then saved
once, with its kind, and needs no marker and no second write. Auto-rotate-all pays nothing extra per
page.

## One route lists every page's kind

`GET /api/projects/{project_id}/page-kinds` returns one row per page, in page order:

```json
{
  "total_pages": 312,
  "reviewed_count": 40,
  "pages": [
    {"page_index": 0, "confirmed_kind": "title page", "reviewed": true,
     "proposed_kind": "unknown", "confidence": null, "run_id": "…"},
    {"page_index": 1, "confirmed_kind": null, "reviewed": false,
     "proposed_kind": "body", "confidence": 0.82, "run_id": "…"}
  ]
}
```

**Every page appears, including pages with no proposal.** A person needs to see a page the
classifier skipped, and an agent triaging the book needs the same list.

**The route reads each journal once.** It reads the proposal journal once and keeps each page's
latest proposal. It reads the reviewed journal once and keeps each page's latest marker. A 500-page
book costs two file reads, not a thousand. This follows the book review queue route, which is tested
for one read per journal.

**`confirmed_kind` comes from the live page when loaded, otherwise from the latest marker.** With
history markers, and with re-OCR and rotation keeping the kind, the two agree. A reviewed page
whose marker predates the `kind` field and which is not loaded reports `confirmed_kind: null` with
`reviewed: true`. The list shows that as "reviewed, kind not recorded".

## One route confirms many pages

`POST /api/projects/{project_id}/page-kinds/confirm` takes a list of pages and the kind for each:

```json
{"pages": [{"page_index": 1, "kind": "body"}, {"page_index": 2, "kind": "body"}], "note": null}
```

**Each page is confirmed exactly as the single-page route confirms it.** Extract the body of
`confirm_page_kind` into one function that both routes call. Under that page's lock, it sets
`page.page_kind` and saves the page to the store. Only after the save succeeds does it write the
reviewed marker. It restores the prior kind if the save fails. One code path means the bulk route
cannot drift from the single one.

**A page not in memory is loaded through `ensure_page_model`, with OCR turned off.** Pages load
lazily when someone opens them, so most pages of a book are not in memory. `ensure_page_model` in
`core/page_state.py` does more than probe storage. Under the project lock, it tries `load_labeled`
then `load_cached`, creates the `PageState`, stamps its `page_id`, and applies the character
sidecars. The save and the marker both need that `page_id`. Calling the loader directly would skip
all of it.

Add a keyword to `ensure_page_model`, `allow_ocr`, defaulting to `True`. With `allow_ocr=False`, it
returns `None` instead of calling `run_ocr` when neither lane has content. Confirming a kind must
never start OCR.

The bulk route loads each page this way, releases the project lock, and only then takes that page's
lock to confirm. That is the order a page fetch followed by an edit already uses. A page that returns
`None` is reported as not loaded and left alone.

Loading leaves each page in memory, as opening it would. Confirming a whole book holds every page's
`Page` in memory until the project is unloaded, the same as paging through the book.

**The response reports each page, and the request succeeds as a whole.** It returns `200` with one
result per requested page and a count:

| status | meaning |
|---|---|
| `confirmed` | the kind was saved and the marker written |
| `not_loaded` | no stored or cached content; nothing written |
| `store_unavailable` | no event store or no `page_id`; nothing written |
| `persist_failed` | the store write failed; the prior kind was restored |

A page index outside the book, or the same index twice, fails the whole request with `400` before
any page is written. The request is capped at the book's page count.

The optional `note` is written onto every marker the request creates, the same way the single route
writes it onto its one marker.

**The route stays synchronous, and the SPA sends at most 25 pages per request.** Measured
2026-09-17 on 32 real OCR'd pages of `projectID3fc3d7d03c613`: a bulk confirm took 1.7 seconds,
about 53 ms a page, and never called `run_ocr`. That is under the ten-second limit this design set,
but a 300-page book in one request would take about 16 seconds by the same rate. Batches of 25 take
about 1.3 seconds each, show progress between them, and need no background job.

## The page toolbar shows and confirms the current page's kind

A kind control sits beside `page-source-badge` in `PageActionsCompact`. It shows one of three
states:

- **Confirmed:** the kind, marked as confirmed.
- **Proposed:** the proposed kind with its confidence, marked as unconfirmed. An `unknown` proposal
  shows as "Kind unknown".
- **Nothing yet:** "No page kind", with a hint to run Propose page kinds.

Opening the control shows a native select of all fourteen kinds, preselected to the confirmed or
proposed kind, and a Confirm button. This is the pattern `RoleSelect` in `RegionDetail.tsx` already
uses for region roles, including its exhaustive `Record` over the union so a new kind fails to
compile until it is listed.

Confirm calls the single-page route through a new `useConfirmPageKind` hook in
`hooks/usePageMutations.ts`. On success it invalidates `["page", projectId, pageIndex]` and the
`["page-kinds", projectId]` prefix.

## A book-wide list reviews many pages at once

A new dialog, opened from the page actions menu as "Review page kinds", lists every page from the
book route. It is a new `pageKinds` key in `stores/dialog-store.ts`.

**Each row shows** the page number, the proposed kind and confidence, and the confirmed kind or
"unreviewed". Clicking a page number closes the dialog and navigates to that page.

**The list starts filtered to unreviewed pages.** A filter chooses unreviewed or all pages, and
another narrows to one proposed kind. Together they turn "confirm every body page" into filter,
select all, confirm.

**Rows have checkboxes, and a bar acts on the selection.** This follows the look and behavior of the
`Worklist` checkbox rows and the `BulkActions` bar, which shows "N selected" once anything is
selected. It does not reuse those components: both are bound to one page's line matches,
`worklistStore`, and page-scoped actions. The dialog keeps its own selection state and its own bar.
The bar offers two actions:

- **Confirm as proposed.** Each selected page is confirmed as its own proposed kind. Pages whose
  proposal is `unknown` or missing are left out, and the bar says how many.
- **Set kind.** A kind select and an apply button confirm every selected page as that one kind.

Both call the bulk route, 25 pages per request, and a loading toast shows how many pages are done
after each request. If a request fails outright, the toast says how many pages were confirmed before
it and stops. On completion a toast reports how many pages were confirmed and names any that were
not, by status. The hook invalidates the `["page-kinds", projectId]` prefix and the
`["page", projectId]` prefix, because any page in the book may have changed.

**A proposal run and page history both refresh the list.** When a Propose page kinds job completes,
`PageActionsCompact` invalidates the `["page-kinds", projectId]` prefix alongside what it invalidates
today. `useUndoPage` and `useRedoPage` in `hooks/usePageMutations.ts` invalidate the same prefix,
because an undo can change a page's kind.

## Confirming in bulk counts as a person's confirmation

**A bulk confirm is a human action, so it writes the page blob.** The provenance design reserves the
page blob for human action. A person who filters the list, looks at the rows, selects them and
presses Confirm has acted, just across many pages. The marker's `method: bulk` keeps that
distinction for anyone who later weighs these labels.

**No rule confirms pages the person did not select.** There is no "confirm everything above 0.8"
action. Page-kind confidence is the page's fit to its book template, not a calibrated probability.

The [geometry region proposals design](2026-09-17-geometry-region-proposals-design.md) measured it at
exactly `0.0` on 288 of 1,089 furniture pages across five corpus books, and on 73 percent of them in
`projectID603d7d5e04ca0`. A threshold on it would confirm and refuse the wrong pages. Selection stays
with the person.

## What changes, file by file

| file | change |
|---|---|
| backend `core/page_kind/reviewed_store.py` | optional `kind` and `method` on the marker; a history marker with no kind withdraws the review; a bulk latest-marker-per-page read |
| backend `core/page_state.py` | `allow_ocr` keyword on `ensure_page_model` |
| backend `api/history.py` | `undo` and `redo` append a history marker when the page's kind changed |
| backend `adapters/ocr/local_doctr.py` and the `PageLoader` protocol in `core/page_state.py` | `run_ocr` takes `page_kind` and sets it before `_ingest_ocr_result` saves the page |
| backend `core/jobs/handlers/reload_ocr.py`, `rotate.py`, `auto_rotate_all.py` | pass the prior confirmed kind to `run_ocr` |
| backend test `PageLoader` doubles in `tests/unit/core/test_page_state.py`, `tests/unit/api/test_b1_b3_f1.py`, `tests/unit/api/test_prefetch.py`, `tests/integration/test_reload_ocr_job.py`, `test_rotate_job.py`, `test_auto_rotate_all_job.py` | accept the `page_kind` keyword on `run_ocr` |
| backend `core/page_kind/proposal_log.py` | a latest-proposal-per-page read over one journal pass |
| backend `api/pages.py` | `page_kind_proposal` on `PagePayload`; extract the confirm body into a shared function |
| backend `api/page_kinds.py` (new) | `GET .../page-kinds` and `POST .../page-kinds/confirm` |
| `frontend/src/api/types.ts` | regenerated with `make openapi-export` |
| `frontend/src/hooks/usePageMutations.ts` | `useConfirmPageKind`; undo and redo invalidate the page-kinds list |
| `frontend/src/hooks/usePageKinds.ts` (new) | the book list query and the bulk confirm mutation |
| `frontend/src/components/PageActionsCompact.tsx` | the kind control, the menu entry, list invalidation on run completion |
| `frontend/src/components/PageKindsDialog.tsx` (new) | the book-wide list, filters, selection and bulk bar |
| `frontend/src/stores/dialog-store.ts` | the `pageKinds` dialog key |
| `tests/e2e/` | one browser test: confirm one page from the toolbar, then bulk confirm from the list |

## What this increment does not build

- **A keyboard path for page kinds.** The matches hotkeys hold plain `j`, `k` and `g` across the
  whole project page, and there is no page-level hotkey scope yet. Choosing keys is its own small
  design.
- **Page kinds in the review queue.** The queue answers for regions only. Adding page kinds to its
  count and to `[` and `]` waits until this surface has been used on a book.
- **Detectors that use confirmed kinds.** Region proposal still reads the measured page class.

## Related

- [Book review queue](2026-09-17-book-review-queue-design.md) — the first increment of slice 5.
- [Region provenance and persistence](2026-09-07-region-provenance-and-persistence-design.md) —
  "Page kind needs a marker, not a decision log".
- [Labeling track roadmap](../plans/2026-09-07-labeling-track-roadmap.md) — slice 5.
