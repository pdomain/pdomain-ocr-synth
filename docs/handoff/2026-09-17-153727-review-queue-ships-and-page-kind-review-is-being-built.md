---
kind: handoff
status: "active"
created: "2026-09-17"
created_at: "2026-09-17T15:37:32Z"
owner: CT
branch: master
scope: pgdp-synthesis
worktree: /workspaces/pdomain/pdomain-ocr-synth
base_commit: "63b6589ef42fcd3a4576e7101691c5bac522fe56"
supersedes: "2026-09-17-122456-slice-3-ships-and-the-region-pipeline-works-on-a-real-book.md"
handoff_reason: material_resume_change
host: claude-code
---

# The book review queue shipped, and page-kind review is being built

## Read this first

**A person can now move through a whole book's region proposals without hunting.** `]` and `[` jump
to the next or previous page with undecided proposals, the rail badge shows how many remain, and a
re-run no longer brings back regions a person already confirmed. Merged to labeler master as
`87e4a7d` and pushed.

**Page-kind review is designed and its backend is in progress** on labeler branch
`feature/page-kind-review`, worktree
`/workspaces/pdomain/pdomain-ocr-labeler-spa/.worktrees/page-kind-review`. Nothing on that branch is
merged. The design is `docs/specs/2026-09-17-page-kind-review-design.md`.

**Master is pushed everywhere.** `pdomain-ocr-labeler-spa` at `3087aa0`, `pdomain-ocr-synth` at
`63b6589` before this handoff. The labeler backend suite passes at 1751 with 4 skipped, the frontend
suite at 1757, and all three region browser tests pass.

## What landed since the previous handoff

| labeler commit | what |
| --- | --- |
| `86105eb` | furniture detection hardened on real books: tall-band skip, folio punctuation, digit edge peel |
| `87e4a7d` | decision carry-forward, the `regions/review-queue` route, `[` and `]`, the rail badge |
| `3087aa0` | current-state records carry-forward and the queue |

The gap-threshold caveat from the previous handoff is closed: head and folio split 17 of 17 pages on
`projectID3fc3d7d03c613`, 20 of 20 on `projectID408c1dd9b9318`, and 22 of 23 on
`projectID657550412c8dc`. The one miss is a folio OCR'd as `IO`.

## How carry-forward and the queue behave

- **A new proposal matching a confirmed region carries its decision.** Same role and box IoU of at
  least 0.7 gives a `carried` decision naming the region, with the new proposal's own ids and the
  origin accepted or edited decision in `carried_from_*`. The carry runs under the page lock, in a
  worker thread.
- **Deleting a region rejects every proposal whose latest decision names it,** not only the source
  proposal.
- **The queue and the page view share one predicate,** `is_undecided` in `core/regions/resolver.py`,
  so they cannot disagree.
- **The `]` selection survives the page change** through `stores/review-selection-intent-store.ts`.
  Any other navigation abandons it, and pressing `[` or `]` before the queue loads says so instead
  of claiming there is no work.

## Page-kind review, in brief

The classifier proposes only `body`, `chapter opening` or `unknown`, and no route or screen showed
proposals at all. The design adds the latest proposal to `PagePayload`, a book route
`GET .../page-kinds`, a bulk `POST .../page-kinds/confirm`, a toolbar control, and a book-wide dialog
with checkboxes. Three review rounds changed it materially:

- a bulk confirm loads pages through `ensure_page_model(allow_ocr=False)`, never by running OCR;
- markers record the kind and a `method`, and undo or redo that changes the kind writes a `history`
  marker, where a null kind withdraws the review;
- re-OCR, rotation and auto-rotate-all keep a confirmed kind by passing it into `run_ocr`, which
  fixes an existing bug where all three silently dropped it.

There is deliberately no confidence threshold for confirming. Page-class confidence is exactly 0.0
on 288 of 1,089 furniture pages.

## Resume steps

1. **Check the backend implementer's result** on `feature/page-kind-review`. It was asked for seven
   commits and a timing of a bulk confirm on a real OCR'd book. If the real timing exceeds ten
   seconds, the design says to make the bulk confirm a background job; decide that before the
   frontend.
2. **Run one whole-branch Python review, fix, then build the frontend** from the design's file table:
   `useConfirmPageKind`, `usePageKinds`, the toolbar control, `PageKindsDialog`, the `pageKinds`
   dialog key, undo and redo invalidating the page-kinds list, and one browser test.
3. **Run it on a real book before merging.** Confirm kinds on `projectID3fc3d7d03c613` and check the
   list, a rotation, and an undo against stored content after a server restart.
4. Update the roadmap, the labeler's current state, and the design's status, then merge and push.
5. Next candidates after that: bottom-of-page furniture, which needs the mirror of
   `furniture_band_ordinals` in `pdomain-pgdp-measure`; then a keyboard path for page kinds.

## Waiting on the owner

- **A labeler release.** The last tag is `v0.2.0` from 2026-06-06, with about 340 commits since. I
  recommend `scripts/do-release.sh` then `publish-index.sh`, but did not cut one unasked.
- **P2-SELECTION-PAGE:** clear every selection on page change, or carry a page index in
  `SelectionPath`.
- **Carry-forward for hand-drawn regions and for rejections.** The 2026-09-08 ruling covers neither;
  both are left undecided in the queue design.
- **OCR lookalike folios** such as `IO` for `10`, deferred on a single example.

## Operating notes

- **Real-book harness:** `/workspaces/pdomain/.m15f-evidence/real-book-region-run/`. OCR runs on the
  GPU at roughly 5 seconds a page after the models load.
- **Frontend gate,** from `frontend/`: `mise exec -- pnpm test`, `mise exec -- pnpm exec tsc -b
  --noEmit`, `lint` (master has 410 warnings), `format:check`. A fresh worktree needs
  `mise exec -- pnpm install --frozen-lockfile`.
- **Browser tests:** `make frontend-build AI=1`, then
  `uv run --group e2e pytest tests/e2e/<file> -n 0` with
  `PLAYWRIGHT_BROWSERS_PATH=/cache/shared-ai/ms-playwright`. Playwright's `]` is `"BracketRight"`.
- **Two branches appending tests to one file conflict in a way a naive per-hunk join breaks.** When
  both only appended, rebuild the file as master's copy plus each branch's tail.
- **Rebuild the SPA before trusting a browser test** after any frontend change; one browser test
  failed on stale toast wording that only a rebuild showed.
- **`basedpyright` on single test files reports 3 old import errors** in
  `tests/integration/test_region_proposals_router.py`; the gate checks `src/` only.

## Parked, not forgotten

- `feature/edition-companion-contract` in the labeler is two commits ahead of master, three weeks
  old, and unrelated.
- `pdomain-ops` has 68 unreleased commits and `pdomain-ocr-training` 56.
- Carried forward: `dict[str, Any]` on `to_dict`/`from_dict` boundaries in `core/page_kind/` and
  `core/regions/`; 490 unreviewed flat-ascender words; the dead AppImage installer; the GPU probe
  raising when the card is full; `BlockDetail`'s dead "model suggests" callout.

## Pointers

- Page-kind review design: `docs/specs/2026-09-17-page-kind-review-design.md`
- Book review queue design, implemented: `docs/specs/2026-09-17-book-review-queue-design.md`
- Roadmap, slice 5: `docs/plans/2026-09-07-labeling-track-roadmap.md`
- Labeler current state: `/workspaces/pdomain/pdomain-ocr-labeler-spa/docs/context/current-state.md`
- Queue browser test: `/workspaces/pdomain/pdomain-ocr-labeler-spa/tests/e2e/test_review_queue_navigation.py`
- The selection issue:
  `/workspaces/pdomain/pdomain-ocr-labeler-spa/docs/issues/2026-09-17-a-word-or-line-selection-jumps-to-another-item-on-page-change.md`
- Previous handoff: the file named in this document's `supersedes` frontmatter
