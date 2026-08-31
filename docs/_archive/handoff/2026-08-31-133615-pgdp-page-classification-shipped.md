---
kind: archive
status: retired
created_at: "2026-08-31T13:36:15Z"
owner: "CT"
branch: "fix/pgdp-fragmented-band-v2"
scope: "pgdp-synthesis"
worktree: "/workspaces/pdomain/pdomain-ocr-synth/.worktrees/pgdp-fragmented-band-v2"
base_commit: "4a2a4e5c28a4b6d28432091120a2170c4dec4150"
supersedes: "2026-08-24-222343-pgdp-synthesis-version-decision.md"
handoff_reason: "stopping"
host: "claude-code"
created: "2026-08-31"
last_verified: "2026-08-31"
---

# PGDP page classification shipped

> **Retired — superseded by `docs/handoff/2026-08-31-183553-m15b-gates-pass-and-merged.md`.**

## Goal

Reach the unchanged M15b gates of 98 percent accepted-line precision, 70 percent eligible-page
coverage, and zero accepted declared-complex pages.

## Done

Three extractor defects were diagnosed and corrected. All work is on
`fix/pgdp-fragmented-band-v2`, unpushed, with `make ci AI=1` green at every commit.

- Corrected `fragmented_band`, which rejected a whole page whenever one ink band split into more
  than one cluster. Version 2 merges clusters that overlap horizontally, ignores clusters under 2
  percent of a band's ink, and excludes only above a 0.35 fragmented-band rate.
- Dropped speck bands holding under 5 percent of a page's median band ink, which were becoming
  candidates that matched no source line.
- Added `profile-pgdp --whole-book`, which measures every page in a project directory but emits only
  the ranked pages, so book statistics describe the book rather than the ranking.
- Added `first_band_top_px` as a pooled book estimate with its median absolute deviation.
- Added `page_templates.py`, which fits per-book normal recto, normal verso, and chapter-opening
  templates and classifies each page, naming the band ordinals the aligner must ignore.
- Suppressed running heads in the extractor and re-swept the candidate box mode, which changed the
  answer from `dominant` to `union`.
- Published `pgdp-profile/v2` and `pgdp-alignment/v3` with retained v1 and v2 schema files.

On the fixed 25-page selection, `fragmented_band` exclusions fell from 23 to 5, accepted pages rose
from 0 to 7, and eligible-page coverage reached 0.538.

## Not done

- Accepted-line precision is undefined. It needs a human confusion ledger.
- Eligible-page coverage is 0.538 against the 0.70 gate.
- Issue 403 is open. Both M15b plans stay `partial`.
- Nothing fits typography from an aligned page, and nothing synthesises a page from a book profile.

## Current evidence

Two `align-pgdp` runs were byte-identical with report SHA-256
`525c7604c944ceb4e794cbefdb62f0fba7cc78cd58d65fe0550f17568c401627` against profile SHA-256
`d7ea14ac83e35207c4d02b53b5b9ea5ba4964bf251d99976f495f2653d2782ae`.

Page reconciliation is 13 eligible, 10 unavailable or malformed, 2 declared complex, 0 source
changed. The seven accepted pages are `089`, `118`, `161`, `p006`, `p148`, `p155`, and `p179`.

All 216 matches across those seven pages run in strictly increasing source and candidate order, and
the first and last match of each carries the right text. No shifted page remains. That check was
read from the report and the overlays, not signed off line by line, so it is not the ledger the
precision gate requires.

The five eligible pages that remain unaccepted all fail on uniqueness margin. Four come from the two
books whose first-band deviation exceeds 2px, which fit no templates, so their running heads were
never suppressed.

## Decisions

- Keep the three gates unchanged at 98 percent precision, 70 percent coverage, and zero accepted
  declared-complex pages.
- The head window minimum is 8px, not the 2px steadiness figure. Running heads measured 0 to 4px off
  their book median while the nearest genuine top-of-page text sat 76px below, and the share of
  pages joining a normal template is flat between a 4px and 20px window.
- Front matter and plates get no page class. Neither has a discriminator the corpus supports and
  both fall to `unknown`, which suppresses nothing.
- Classification constants live in the profile methods, not the alignment methods, because
  classification runs in the profile.
- Earlier wire versions are retained as schema files and git history. Loading an old major version
  fails validation by design.

## Open decisions

- Whether 70 percent coverage is the right target. The end goal is synthesising OCR training data,
  which needs enough correctly measured pages per book rather than a high fraction of them.
  Precision protects the fitted style; coverage only sets how much evidence a book yields. The M15b
  design calls both thresholds conservative seed values for corpus review to calibrate.
- How to classify books with no stable type page, which is what blocks four of the five remaining
  eligible pages.
- Whether to commit the evidence directory, which currently lives outside the repo.

## Failed approaches and cautions

- Do not fit templates on the emitted profile pages. On the five review books that gives first-band
  deviations of 2.0, 5.0 and 3.0 where the whole books give 1.0, 18.5 and 0.0. Templates must be
  fitted inside `profile_project` over the measured pages.
- Do not reuse the 2px book-steadiness figure as the per-page head window. At 2px, `p179.png` goes
  unclassified and stays misaligned.
- Do not choose `union` for the candidate box before running heads are suppressed. Spanning a head
  band and its folio produces a body-line shape the aligner matches a source line to, which
  regressed pages that had been correct.
- Do not read a high uniqueness margin as evidence of a correct alignment. Removing a spare
  candidate can leave only one monotone assignment, which raises the margin whether or not the
  assignment is right.
- Preserve `.venv-container` during CI. Move it to a unique temporary directory, set only
  `UV_PROJECT_ENVIRONMENT` to `.venv`, and restore it afterward. Left in place it enters the source
  distribution and fails the build.
- Every CLI flag must appear in the spec flag table or `test_argparse_flags_match_spec_01` fails.

## Pointers

- Page template design: `docs/specs/2026-08-31-pgdp-whole-book-page-templates-design.md`
- Page classification plan: `docs/plans/2026-08-31-pgdp-page-classification.md`
- Fragmented-band design: `docs/specs/2026-08-31-pgdp-fragmented-band-correction-design.md`
- Fragmented-band plan: `docs/plans/2026-08-31-pgdp-fragmented-band-correction.md`
- Classifier: `src/pdomain_ocr_synth/pgdp/page_templates.py`
- Extractor: `src/pdomain_ocr_synth/pgdp/alignment_image.py`
- Profiling: `src/pdomain_ocr_synth/pgdp/profiling.py`
- Classifier tests: `tests/test_pgdp_page_templates.py`
- Evidence, reports, overlays and scripts: `/workspaces/pdomain/.m15b-evidence/`
- Review overlays for the 13 eligible pages: `/workspaces/pdomain/.m15b-evidence/overlays-v3/`
- Follow-up tracker: `ConcaveTrillion/ocr-container-meta#403`

## Resume steps

1. Use the docgraph pickup-handoff skill for scope `pgdp-synthesis` in this worktree.
2. Settle the coverage question before more extractor work. If 70 percent stands, the next target is
   books with no stable type page. If it does not, record the new target and its reasoning first.
3. Build the confusion ledger over the seven accepted pages from the overlays, recording a reviewer
   decision per operation, and measure accepted-line precision.
4. Rerun the fixed selection, confirm byte-identical replay, and record the counts in the page
   classification plan.
5. Mark both M15b plans `implemented` and close issue 403 only if all three gates pass.
6. Use the finishing-a-development-branch skill to integrate `fix/pgdp-fragmented-band-v2`.
