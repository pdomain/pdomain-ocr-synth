---
kind: handoff
status: "active"
created: "2026-08-24"
created_at: "2026-08-24T13:06:47Z"
owner: CT
branch: master
scope: pgdp-synthesis
worktree: /workspaces/pdomain/pdomain-ocr-synth
base_commit: cf07aee21f1dbeb9e55afbd1b2c85908688b9ad8
supersedes: ""
---

# PGDP synthesis next steps

## Goal

Build scan-derived typography and page-structure synthesis in conservative,
measured slices. The immediate task is to correct M15b fragmented-band
exclusions and pass its existing corpus gates before starting later typography,
semantic, or compositor work.

## Done

- M14 ships deterministic local PGDP ranking and bounded review queues through
  `rank-pgdp` and `pgdp-rank/v1`.
- M15a ships deterministic source-frame foreground and ink-band profiling
  through `profile-pgdp` and `pgdp-profile/v1`.
- M15b ships lossless F2 source records, formatting spans, scan-row candidates,
  monotone line alignment, `pgdp-alignment/v1`, `align-pgdp`, reviewed fixtures,
  visual overlays, review ledgers, and fixed quality gates.
- M14 and M15a implementation plans were promoted into architecture and retired.
  M15b remains partial.
- Full CI on `master` passed with 1,383 tests passed and 314 skipped.

## Not done

- M15b has not passed accepted-line precision or eligible-page coverage because
  `fragmented_band` rejects visually alignable pages.
- Rotation, rectification, dewarping, verified baselines, typography fitting,
  and font candidate ranking are not implemented.
- Styled typography controls, multi-column composition, tables, horizontal and
  vertical braces and brackets, semantic poetry or blockquote inference, and
  downstream OCR or structure-model evaluation are not implemented.
- The broad typography and structure design remains draft and must not be
  treated as shipped architecture.

## Current evidence

The fixed balanced M15b review used 25 pages from five books. The report held
1,681 raw source-line records and 1,107 operation rows. All 25 pages were
excluded before alignment, so accepted-line precision and eligible-page
coverage were undefined. Visual review found 12 otherwise alignable pages and
359 rows incorrectly excluded by `fragmented_band`. The other 13 pages and 748
rows were conservatively excluded as complex, malformed, or too short.

Two final replays were byte-identical with report SHA-256
`2d71eb3bef6ac953c82b9e581ffa92dc77436f90f592a6952a4ec27a232eb107`.
The reviewed ledger SHA-256 was
`54fd9f18b508e20afb57fec9f3db1415111307747cd9751db22104ca5c56ad8b`.

The fixed page selection was:

- `projectID64a479f51ce5b`: `p006`, `p008`, `p155`, `p090`, `p092`.
- `projectID603d7d5e04ca0`: `089`, `118`, `149`, `161`, `194`.
- `projectID609bfa0449bdf`: `a001`, `a005`, `p055`, `p148`, `p179`.
- `projectID67a80fde44d34`: `002`, `005`, `006`, `021`, `053`.
- `projectID657550412c8dc`: `w0030`, `a0090`, `w0050`, `w0070`, `w0390`.

## Decisions

- Keep the M15b gates unchanged: at least 98% accepted-line precision, at least
  70% eligible-page coverage, and zero accepted declared-complex pages.
- Fix the extractor in a separate review run. Do not weaken thresholds in that
  run.
- Preserve source-frame observations and uncertainty. Do not call ink bands
  baselines or infer exact typefaces without evidence.
- LLM image review may bootstrap tools and labels, but normal profiling and
  synthesis must stay local and model-independent.
- Page structure remains part of the program, including columns, tables,
  reading order, and horizontal and vertical braces and brackets. It starts only
  after the source-line evidence boundary is reliable.

## Failed approaches and cautions

- The first top-ranked 25-page queue was dominated by complex pages and did not
  provide a balanced quality review. Use the fixed selection above.
- Current fragmented-band detection rejects ordinary single-column text rows.
  Treat this as an extractor defect, not evidence that the gates are too strict.
- `.venv-container` can enter source distributions and fail packaging because
  it contains an absolute Python symlink. Preserve it intact, move it to a
  unique temporary directory during CI, set `UV_PROJECT_ENVIRONMENT=.venv`, and
  restore it afterward.

## Pointers

- Current PGDP ranking architecture:
  `docs/architecture/pgdp-ranking-and-review-queue.md`
- Current observed-geometry architecture:
  `docs/architecture/pgdp-observed-geometry-profiling.md`
- Current operational evidence: `docs/context/current-state.md`
- Active and deferred intent: `docs/context/intent-map.md`
- Partial M15b plan:
  `docs/plans/2026-08-23-pgdp-source-line-alignment.md`
- Broad draft design:
  `docs/specs/2026-08-22-pgdp-typography-structure-synthesis-design.md`
- Alignment extraction and orchestration:
  `src/pdomain_ocr_synth/pgdp/alignment_image.py`
  and `src/pdomain_ocr_synth/pgdp/alignment.py`
- Review helpers: `src/pdomain_ocr_synth/pgdp/alignment_review.py`
- Focused tests: `tests/test_pgdp_alignment_image.py`,
  `tests/test_pgdp_alignment.py`, and `tests/test_pgdp_alignment_review.py`
- Follow-up tracker: `ConcaveTrillion/ocr-container-meta#403`

## Resume steps

1. Use the docgraph pickup-handoff skill for scope `pgdp-synthesis`.
2. Inspect issue 403, the M15b plan, current extractor code, and focused tests.
3. Create an isolated worktree and a focused implementation plan for the
   fragmented-band extractor correction.
4. Reproduce the 12 false exclusions with regression fixtures before changing
   extraction behavior.
5. Rerun the fixed 25-page selection, deterministic replay, visual ledger, full
   CI, and docgraph checks without changing the gates.
6. Mark M15b implemented and promote it into architecture only after all three
   quality gates pass. Then plan the next measured slice.
