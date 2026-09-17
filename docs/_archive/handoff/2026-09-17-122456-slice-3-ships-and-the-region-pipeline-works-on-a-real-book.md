---
kind: archive
status: retired
created_at: "2026-09-17T12:24:56Z"
owner: "CT"
branch: "master"
scope: "pgdp-synthesis"
worktree: "/workspaces/pdomain/pdomain-ocr-synth"
base_commit: "94dd97548c572efcef86a788feae0465afd7ce44"
supersedes: "2026-09-17-102343-slice-4-ships-geometry-engine-live-gap-threshold-next.md"
handoff_reason: "material_resume_change"
host: "claude-code"
created: "2026-09-17"
last_verified: "2026-09-17"
---

> **Retired — superseded by `docs/handoff/2026-09-17-153727-review-queue-ships-and-page-kind-review-is-being-built.md`.**


# Slice 3 shipped, and the region pipeline works on a real book

## Read this first

**A person can now review machine-proposed regions on a real book.** The labeler proposes a running
head and a folio on real DocTR OCR output, and a person accepts, re-roles or rejects each proposal
from the keyboard. Verified on 80 real pages of `projectID657550412c8dc`: 29 proposals on 15 pages,
and an accepted header served back at exactly its pixel box.

**Until the last hour, the pipeline had never worked on real data.** Every region test built
pixel-space pages; DocTR emits normalized 0-to-1 word boxes. The detector skipped every real page and
accept returned 400. Fixed and merged. **Any new region test should use `normalized_page_loaded`,
not only the pixel-space `toolbar_loaded`.**

**Everything is pushed.** `pdomain-ocr-labeler-spa` is at `0419a31`, `pdomain-ocr-synth` at
`94dd975` before this handoff, `pdomain-pgdp-measure` at `9cf5e7a`, `pdomain-ops` at `02b201a`, all
level with `origin/master`. The labeler's backend suite passes at 1714 with 4 skipped, the frontend
suite at 1728, and both region browser tests pass.

## What landed since the previous handoff

| labeler commit | what |
| --- | --- |
| `6ed5156` | the furniture gap threshold fitted per book by Otsu split, replacing the fixed 10 percent |
| `b8c2cd7` | slice 3, the region review surface, all seven tasks plus the whole-branch review fixes |
| `a42b0b7` | issue P2-SELECTION-PAGE filed |
| `24462af` | region boxes convert at the API boundary; the pipeline works on real OCR pages |

## How the review surface works

Key `5` selects the region rail target, which has a visible cell. A canvas click selects the smallest
region or proposal under it. `RegionDetail` accepts, accepts as another role, or rejects a proposal,
and changes the role of or deletes a confirmed region. From the keyboard, `n` and `p` step through
undecided proposals, `enter` accepts, `x` rejects, and selection advances by itself. `j` and `k` were
avoided because `useMatchesHotkeys` binds them on every page. The page actions menu starts both
proposal runs, and a region run ends with a summary message that says when pages were skipped for
having no page kind.

## What the reviews caught, and why they are worth keeping

**Whole-branch reviews found real defects four times this session**, every one invisible to a
task-scoped review:

- a detector opting into the book-fit step by having any method named `fit`, which a scikit-learn
  model would trigger; it now subclasses `BookFittedDetector`;
- a decision sendable twice, because the keyboard and the panel held separate mutation instances,
  and a reject route that appended duplicate decisions;
- a region selection outliving its page, so a keyboard accept could reach the new page's route with
  the old page's proposal id;
- the detector and accept converting boxes against different frames when the decoded image and the
  page differ in size.

**The real-book run found what no review could.** Tests and reviews all agreed on a convention the
real data does not use. Run on real data before calling anything done.

## Decisions worth knowing

- **The API speaks the page's pixel frame; the page tree stores the page's own convention.** Region
  boxes convert at the boundary in `core/regions/coordinates.py`, as word boxes always have through
  `_bbox_to_model`. The detector works in the page frame and rescales ink bands and text width into
  it from `measurement.source_frame`.
- **A bad region box returns `400 invalid_region_box`,** never `invalid_region_role`.
- **Rejecting a rejected proposal is a no-op.** The decision journal is what confidence will be
  calibrated against, so duplicates would double-count.
- **All four region mutations share one TanStack `mutationKey`**, so a keyboard decision and a panel
  click cannot race.
- **A region selection clears on page change. Word, line and paragraph selections do not.** That
  older behaviour is filed, not changed, because nobody has decided it; see P2-SELECTION-PAGE.

## Resume steps

1. **Recheck the gap-threshold fit on word boxes for the two narrow-valley books.**
   `projectID3fc3d7d03c613` and `projectID408c1dd9b9318` had head-to-folio valleys only 4 and 5 px
   wide, measured from ink. Word-box gaps differ slightly. OCR 40 to 80 pages of each through the
   labeler with the real-book harness in the evidence folder, run `propose_regions`, and check the
   head and folio still split. This closes the last caveat on the per-book fit.
2. **Decide P2-SELECTION-PAGE**, or ask the owner: clear every selection on page change, or carry a
   page index in `SelectionPath`. The issue lays out both.
3. **Next slice candidates**, in the order I would take them:
   - bottom-of-page furniture — footer, catchword, signature mark, press figure — which needs the
     mirror of `furniture_band_ordinals` in `pdomain-pgdp-measure`;
   - page-kind review in the UI, which first needs the proposed kind on `PagePayload`;
   - slice 5, the confidence-ranked review queue across a book.
4. Keep the working method: pre-run plan code against the real classes, run every compile check with
   the exact command the pre-commit hook runs, dispatch implementers per task, parallelize tasks that
   share no files, run a whole-branch review before merge, and run on real data before calling it
   done.

## Operating notes

- **Real-book harness:** `/workspaces/pdomain/.m15f-evidence/real-book-region-run/` holds `run.py`,
  `accept_probe.py` and a README. OCR runs on the GPU at roughly 5 seconds a page after the models
  load.
- **The frontend gate** is `mise exec -- pnpm test`, `mise exec -- pnpm exec tsc -b --noEmit`,
  `lint` and `format:check`, from `frontend/`. `tsc -b` enables `noUnusedLocals`; plain
  `tsc --noEmit` does not, and I was caught out checking with the looser one.
- **A fresh worktree needs `mise exec -- pnpm install --frozen-lockfile`** in `frontend/`. It takes
  about a second from the shared store.
- **Browser tests:** `uv sync --group e2e` is done. Chromium is cached at
  `PLAYWRIGHT_BROWSERS_PATH=/cache/shared-ai/ms-playwright`. Build the SPA with `make frontend-build`
  first. Playwright needs `"Enter"`, not `"enter"`, and canvas clicks need `page.mouse.click`.
- **`git branch -d` checks merge status against the current checkout's branch**, so a branch merged
  into a feature branch reports unmerged from `master`. Confirm with `git merge-base --is-ancestor`
  before using `-D`.
- Lint warnings: master has 410. Check an implementer's "no new warnings" claim by comparing
  per-file counts against master; one claim this session was wrong by eight.

## Parked, not forgotten

- P2-SELECTION-PAGE: word, line and paragraph selections silently move to another item on page
  change.
- `feature/edition-companion-contract` in the labeler is two commits ahead of master and unrelated.
- `pdomain-ops` has 68 unreleased commits and `pdomain-ocr-training` 56; neither blocks this work.
- Carried forward: `dict[str, Any]` on `to_dict`/`from_dict` boundaries in `core/page_kind/` and
  `core/regions/`; 490 unreviewed flat-ascender words; the dead AppImage installer; the GPU probe
  raising when the card is full; `BlockDetail`'s dead "model suggests" callout and its local role
  list.

## Pointers

- Slice 3 design: `docs/specs/2026-09-17-region-review-surface-design.md`
- Slice 3 plan, implemented: `docs/plans/2026-09-17-region-review-surface.md`
- Slice 4 design: `docs/specs/2026-09-17-geometry-region-proposals-design.md`
- Slice 4 plan, implemented: `docs/plans/2026-09-17-geometry-region-proposals.md`
- The gap-threshold issue, fixed with one caveat:
  `docs/issues/2026-09-17-the-furniture-gap-threshold-cannot-be-a-fixed-share.md`
- Roadmap: `docs/plans/2026-09-07-labeling-track-roadmap.md`
- The selection issue:
  `/workspaces/pdomain/pdomain-ocr-labeler-spa/docs/issues/2026-09-17-a-word-or-line-selection-jumps-to-another-item-on-page-change.md`
- The coordinate conversion: `/workspaces/pdomain/pdomain-ocr-labeler-spa/src/pdomain_ocr_labeler_spa/core/regions/coordinates.py`
- Real-book evidence: `/workspaces/pdomain/.m15f-evidence/real-book-region-run/README.md`
- Labeler current state: `/workspaces/pdomain/pdomain-ocr-labeler-spa/docs/context/current-state.md`
- Previous handoff: the file named in this document's `supersedes` frontmatter
