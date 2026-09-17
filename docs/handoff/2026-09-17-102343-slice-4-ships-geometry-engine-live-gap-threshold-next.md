---
kind: handoff
status: "active"
created: "2026-09-17"
created_at: "2026-09-17T10:23:43Z"
owner: CT
branch: master
scope: pgdp-synthesis
worktree: /workspaces/pdomain/pdomain-ocr-synth
base_commit: "8ef2e13774b1424122cf2861e8ceda5ab4adf023"
supersedes: "2026-09-17-030031-page-kind-lands-end-to-end-region-routes-task-5-now-unblocked.md"
handoff_reason: material_resume_change
host: claude-code
---

# Slice 4 shipped, the labeler proposes regions itself, and the gap threshold is next

## Read this first

**The labeler now generates region proposals of its own.** Until this session every proposal in
the system had been written by a test. A book-scoped `propose_regions` run measures the whole book
and proposes a `page header` and a `page number` from each page's top furniture bands.

**Every resume step in the previous handoff is done.** Region-routes Task 5 shipped, the x-height
figure was recomputed and was wrong, slice 4 was designed, planned and shipped, and `page_kind`
reaches a plain `GET`.

**Everything is pushed.** `pdomain-ocr-labeler-spa` is at `0e35a06`, `pdomain-ocr-synth` at
`8ef2e13`, `pdomain-pgdp-measure` at `9cf5e7a`, `pdomain-ops` at `02b201a`, all level with
`origin/master`. The labeler suite is green at 1683 passed and 4 skipped.

**This handoff is a checkpoint, not a stop.** It was written mid-loop because the previous session
ended without one.

## What landed, in the order it landed

| repo | commit | what |
| --- | --- | --- |
| labeler | `cebe556` | region-routes Task 5: `propose_regions` job and `POST .../regions/propose` |
| labeler | `8fd6a02` | four parked page-kind defects, including `page_kind` on `PagePayload` |
| labeler | `0b52899` | both proposal jobs read images through a verified per-page lease |
| labeler | `0e35a06` | slice 4: widened detector seam, shared `measure_book`, furniture detector |
| measure | `6a15401`, `9cf5e7a` | corrected the wrong x-height docstring and usage doc |
| ops | `02b201a` | suite-status doc re-measured; three of its claims were stale |

## Three measurements changed decisions rather than confirming them

**The "43 to 67 percent" x-height figure was a wrong precision figure.** Recomputed over 1,040
pages it is 45 percent pooled and 0 to 85 percent per book, at 50 percent recall. Spread may raise
a heading proposal's confidence and must never gate one. Evidence script and finding are in the
pointers.

**A furniture proposal must not inherit its page's classification confidence.** That score is
exactly 0.0 on 288 of the 1,089 pages carrying a furniture band, 26 percent pooled and 73 and 67
percent in two books. Confidence now comes from the cluster's shape, at 0.8, 0.6 and 0.4, declared
uncalibrated in the code because no region ground truth exists anywhere in the suite.

**No fixed share of text width splits a running head from its folio.** Measured across six books by
projecting each furniture band's ink, the gap distribution is cleanly bimodal every time and the
valley is never in the same place twice. The shipped 10 percent sits inside none of the six. This
is filed, not fixed.

## Decisions worth knowing

**Re-measure rather than persist.** A region run calls `measure_book` again instead of reading a
stored measurement. The page-kind journal has no per-facet staleness machinery, so persisting would
need a new record design. The design doc says what that record would need if speed ever matters.

**A detector failure and a lease failure are reported separately.** Both handlers enter the lease
through `ExitStack`, so only `open_labeling_page`'s own `ValueError` is attributed to the lease. A
detector that raises on one page is logged with its traceback and that page is skipped, rather
than killing a 400-page run.

**Every measurement joins to its page by value, never by position.** `MeasuredBook.page_indices`
exists because a page skipped for a failed lease opens a gap positional recovery cannot see. An
implementer caught this; the brief had missed it.

## What went well, and should keep happening

**Running a plan's own code against the real classes before dispatching an implementer.** It found
five of the twelve errors in the slice 4 plan, including `PageMeasurement` coherence rules, a
normalized box needing coordinates in `[0, 1]`, and a mixed-coordinate page being unbuildable in one
line block.

**The whole-branch review keeps earning its cost.** Four sessions running. This time it found a
quadratic measurement join and a progress bar that ran backwards between two phases, both
invisible to any single task.

**Correcting a running implementer with `SendMessage` when new evidence lands.** The confidence rule
changed mid-task without a wasted round trip.

## Resume steps

1. **Replace the fixed gap share with a per-book Otsu split.** The issue carries the method, the
   six-book evidence, and where it belongs: fit it inside `measure_book`, which already holds every
   page's bands and grayscale threshold, carry it on `MeasuredBook` into `DetectorInput`, and keep
   the detector a pure per-page function. The one book where it matters loses 14 of 109 splits.
2. **Then design slice 3, the region review surface.** It now has something real to display. The
   frontend already carries generated types for every region and page-kind route and no client code
   calling one. A person can see a region on the canvas and cannot accept, reject, or draw one.
   Brainstorm and design first; slices 3 to 7 are unplanned by intent.
3. **Consider running the detector on a real book end to end.** No stored OCR word geometry exists
   for the corpus books, so this needs OCR through the labeler first. It would also let the gap
   threshold be rechecked against word boxes rather than ink runs.
4. Keep using `superpowers:subagent-driven-development`, `writing-python:python-implementer` per
   task, the whole-branch review before merge, and pre-running plan code against real classes.

## Parked, not forgotten

- **Bottom-of-page furniture.** `furniture_band_ordinals` covers top bands only. Footer, catchword,
  signature mark and press figure need the mirror logic in `pdomain-pgdp-measure`.
- **Store-less mode is inconsistent.** The confirm route requires the event store; every other
  mutation route degrades without it. A design question, left open.
- **`feature/edition-companion-contract`** in the labeler is two commits ahead of master, from
  2026-08-23, unrelated to the labeling track. Nobody has said what it waits on.
- **`pdomain-ops` has 68 unreleased commits and `pdomain-ocr-training` 56.** Neither blocks the
  labeling track.
- **Large pre-existing basedpyright backlogs under `tests/`**, in the labeler and in
  `pdomain-pgdp-measure`. The repos' own `make lint` scopes basedpyright to `src/` only.
- Carried forward unchanged from the previous handoff: `dict[str, Any]` on every `to_dict`/
  `from_dict` boundary in `core/page_kind/` and `core/regions/`; `set_region_word_membership`'s
  missing mixed-coordinate guard; 490 unreviewed flat-ascender words; the dead AppImage installer for
  `pdomain-ocr-simple-gui`; the GPU probe raising when the card is full.

## Operating notes

**Real corpus page images live at `/workspaces/pdomain-data/pgdp-corpus/projectID*/`.** Measuring
80 pages with `profile_page` takes a minute or two. A prefix of a book is not the book: a 120-page
prefix of `projectID603d7d5e04ca0` fits no templates at all, while the full book fits three.

**Evidence scripts go in `/workspaces/pdomain/.m15f-evidence/`.** Four were written this session.
Give each a non-default output file name when it takes arguments, or a second run overwrites the
artifact a document cites.

**The labeler's venv must be on `PATH` to commit** or pre-commit fails. `git stash` is shared across
worktrees and sessions; use a tagged push and apply by SHA.

**Commit subjects must stay within 72 characters.** No GitHub workflows exist; releasing runs from
`scripts/release-common.sh` and publishing to an index is a separate manual step.

## Pointers

- Slice 4 design: `docs/specs/2026-09-17-geometry-region-proposals-design.md`
- Slice 4 plan, implemented, carrying its corrections inline:
  `docs/plans/2026-09-17-geometry-region-proposals.md`
- The gap-threshold issue, resume step 1:
  `docs/issues/2026-09-17-the-furniture-gap-threshold-cannot-be-a-fixed-share.md`
- The x-height finding: `docs/research/2026-09-17-x-height-spread-does-not-find-chapter-openings.md`
- The page-kind issue, all five items fixed:
  `docs/issues/2026-09-16-page-kind-follow-ups-parked-during-tasks-6-and-7.md`
- Roadmap: `docs/plans/2026-09-07-labeling-track-roadmap.md`
- Region routes plan, all eight tasks shipped: `docs/plans/2026-09-08-region-routes-and-proposal-run.md`
- The furniture detector: `/workspaces/pdomain/pdomain-ocr-labeler-spa/src/pdomain_ocr_labeler_spa/core/regions/furniture.py`
- The shared measurement pass: `/workspaces/pdomain/pdomain-ocr-labeler-spa/src/pdomain_ocr_labeler_spa/core/page_measurement.py`
- Evidence scripts:
  - `/workspaces/pdomain/.m15f-evidence/xheight_spread_vs_page_class.py`
  - `/workspaces/pdomain/.m15f-evidence/furniture_band_coverage.py`
  - `/workspaces/pdomain/.m15f-evidence/page_class_confidence_on_furniture.py`
  - `/workspaces/pdomain/.m15f-evidence/furniture_band_gap_threshold.py`
- Suite status: `/workspaces/pdomain/pdomain-ops/docs/plans/2026-09-12-suite-status-and-agent-allocation.md`
- Previous handoff: the file named in this document's `supersedes` frontmatter
