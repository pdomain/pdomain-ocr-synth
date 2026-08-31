---
kind: archive
status: retired
created_at: "2026-08-24T22:23:43Z"
owner: "CT"
branch: "master"
scope: "pgdp-synthesis"
worktree: "/workspaces/pdomain/pdomain-ocr-synth"
base_commit: "70e0811991a3bbb88d9e271b2c6ae1a86f39e9a7"
supersedes: "2026-08-24-130626-pgdp-synthesis-next-steps.md"
created: "2026-08-24"
last_verified: "2026-08-31"
---

# PGDP synthesis version decision

> **Retired — superseded by `docs/handoff/2026-08-31-133615-pgdp-page-classification-shipped.md`.**

## Goal

Decide the report version before planning or changing code. Then correct the
M15b `fragmented_band` extractor defect on the fixed 25-page review set. Keep
the existing quality gates unchanged.

## Done

- Picked up and validated the prior `pgdp-synthesis` handoff.
- Confirmed that its commit delta contains only the landed handoff file.
- Confirmed that every handoff pointer still exists.
- Confirmed that the worktree is clean on `master` at commit `70e0811`.
- Confirmed that issue 403 is open and no open pull request competes with this work.
- Read the M15b design, partial plan, current state, intent map, extractor code,
  focused tests, and corpus review artifacts.
- Confirmed that `/tmp/pdomain-m15b-corpus.PUlPdU` still contains the balanced
  reports, ledger builder, and confusion ledger.

## Not done

- No design choice was approved.
- No isolated implementation worktree was created.
- No plan, test, source, report, ledger, or context file was changed.
- No focused tests, corpus replay, full CI, or docgraph completion checks ran.
- M15b remains partial.

## Current evidence

The fixed review contains 25 pages from five books and 1,107 operation rows.
All 25 pages were excluded before alignment. Visual review found that
`fragmented_band` incorrectly excluded 12 otherwise alignable pages and 359
rows. The other 13 pages and 748 rows were conservatively excluded.

Two final reports were byte-identical with SHA-256
`2d71eb3bef6ac953c82b9e581ffa92dc77436f90f592a6952a4ec27a232eb107`.
The reviewed ledger SHA-256 was
`54fd9f18b508e20afb57fec9f3db1415111307747cd9751db22104ca5c56ad8b`.

The current join rule caps the horizontal gap at twice the median component
height. Initial inspection suggests that ordinary word spacing can exceed the
cap and leave several clusters in one text band. Before choosing a correction,
the next session must verify that cause against the 12 reviewed scans.

## Decisions

- Keep the gates at 98% accepted-line precision, 70% eligible-page coverage,
  and zero accepted declared-complex pages.
- Preserve deterministic replay and the fixed 25-page selection.
- Do not begin later typography, semantic, compositor, or rectification work.
- Do not change extraction behavior until the report-version choice is approved.

## Open decision

The current M15b design requires `pgdp-alignment/v2` when an extractor threshold
changes. Use `v2` unless the owner explicitly approves a design change that
preserves `v1`. Existing code and stored reports must remain available for exact
`v1` replay.

## Failed approaches and cautions

- Do not weaken the three corpus gates to make the review pass.
- Do not treat the 12 false exclusions as evidence that their pages are complex.
- Do not create a nested worktree. First run the worktree isolation check from
  the resumed checkout.
- Preserve `.venv-container` intact during CI. Move it to a unique temporary
  directory. Set only the `UV_PROJECT_ENVIRONMENT` name to use `.venv`. Restore
  it afterward.

## Pointers

- Prior handoff: `docs/_archive/handoff/2026-08-24-130626-pgdp-synthesis-next-steps.md`
- M15b design: `docs/specs/2026-08-23-pgdp-source-line-alignment-design.md`
- Partial M15b plan: `docs/plans/2026-08-23-pgdp-source-line-alignment.md`
- Current state: `docs/context/current-state.md`
- Active intent: `docs/context/intent-map.md`
- Extractor: `src/pdomain_ocr_synth/pgdp/alignment_image.py`
- Focused extractor tests: `tests/test_pgdp_alignment_image.py`
- Alignment tests: `tests/test_pgdp_alignment.py`
- Review tests: `tests/test_pgdp_alignment_review.py`
- Corpus report: `/tmp/pdomain-m15b-corpus.PUlPdU/alignment-balanced-final-a.json`
- Replay report: `/tmp/pdomain-m15b-corpus.PUlPdU/alignment-balanced-final-b.json`
- Corpus ledger: `/tmp/pdomain-m15b-corpus.PUlPdU/confusion-ledger.json`
- Ledger builder: `/tmp/pdomain-m15b-corpus.PUlPdU/build_ledger.py`
- Follow-up tracker: `ConcaveTrillion/ocr-container-meta#403`

## Resume steps

1. Use the docgraph pickup-handoff skill for scope `pgdp-synthesis` in this
   worktree.
2. Confirm `pgdp-alignment/v2` for the extractor correction. Preserve `v1` only
   if the owner explicitly approves the required design change.
3. Verify the suspected word-gap cause on all 12 reviewed false exclusions.
4. Present two or three bounded extractor approaches and obtain design approval.
5. Write the approved design and focused implementation plan under `docs/specs/`
   and `docs/plans/` using the repository docgraph workflow.
6. Create or enter an isolated implementation worktree before changing code.
7. Add regression fixtures for the 12 false exclusions before changing the
   extractor.
8. Rerun the fixed corpus review, deterministic replay, visual ledger, focused
   tests, full CI, and strict docgraph checks without changing the gates.
9. Mark M15b implemented only after all three gates pass.
