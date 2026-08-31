# PGDP Page Classification Implementation Plan

## Agent Index

- **Kind:** plan
- **Status:** implemented
- **Owner:** CT
- **Created:** 2026-08-31
- **Last verified:** 2026-08-31
- **Provenance:** derived from the approved whole-book page template design and first-band geometry
  measured across 41 whole PGDP books on 2026-08-31
- **Disposition:** Classification, suppression, and the two template-fitting corrections shipped; all three gates pass.
- **Read when:** implementing book templates, page classes, or running-head suppression.
- **Search terms:** PGDP, M15a, page class, type page, running head, template, recto, verso.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Classify every page against its book's measured templates, and stop the aligner matching
source lines to running heads.

**Architecture:** Profile whole books, fit first-band templates per book, classify each page, and
emit the class in `pgdp-profile/v2`. The extractor reads the class and suppresses furniture bands as
`pgdp-alignment/v3`.

**Tech Stack:** Python 3.13, frozen dataclasses, Pydantic, Pillow, NumPy, argparse, pytest, Ruff,
basedpyright, JSON Schema.

---

## Goal

Remove the one defect that puts accepted-line precision near 62 percent, and give later stages a
book geometry they can rely on.

## Architecture

Keep measurement in M15a and consumption in M15b. The profile gains book templates and a per-page
class; the extractor gains a suppression step keyed on that class and nothing else.

## Tech Stack

Use only the repository's installed Python, Pydantic, Pillow, NumPy, argparse, pytest, Ruff, and
basedpyright dependencies.

## Global Constraints

- Follow [the whole-book page template
  design](../specs/2026-08-31-pgdp-whole-book-page-templates-design.md).
- Preserve `pgdp-rank/v1`, `pgdp-profile/v1`, and `pgdp-alignment/v1` and `v2` byte compatibility.
- Do not change the two corpus gates: 98 percent accepted-line precision and zero accepted
  declared-complex pages. The 70 percent eligible-page coverage gate was replaced on
  2026-08-31 by per-book admission at 30 accepted pages; see
  `docs/specs/2026-08-31-pgdp-whole-book-yield-gate-design.md`.
- Do not change the alignment thresholds: 90 percent matched lines, cost at most 0.22, uniqueness
  margin at least 0.15.
- Keep the fixed 25-page selection fixed and replay deterministic.
- Add no OCR engine. Every measurement comes from ink-band geometry.
- Do not read adjacent pages. Templates are book-level statistics, and the extractor still decodes
  one scan at a time.
- Run `make ci AI=1` after focused checks and before every implementation commit.
- Preserve `.venv-container` intact during CI. Move it to a unique temporary directory, set only
  `UV_PROJECT_ENVIRONMENT` to `.venv`, and restore it afterward.

## Task 1: Profile whole books while emitting the selected pages

**Files:**

- Modify: `src/pdomain_ocr_synth/pgdp/profile_input.py`
- Modify: `src/pdomain_ocr_synth/pgdp/profiling.py`
- Modify: `src/pdomain_ocr_synth/cli.py`
- Modify: `tests/test_pgdp_profile_input.py`
- Modify: `tests/test_cli_profile_pgdp.py`

Templates describe a book, so they must be fitted over every page of it. But alignment costs about
1s per page against profiling's 9.5ms, and the fixed 25-page selection must not move. So this task
separates what is measured from what is emitted.

- [x] **Step 1: Write failing tests for whole-book enumeration**

Assert that with the new mode a project measures every `*.png` under its directory, not only the
pages the M14 ranking named, and that the emitted report still contains exactly the ranked pages.
Assert the pooled estimates report a `sample_count` equal to the number measured, not the number
emitted. Assert the default mode is unchanged.

Cover a project directory holding a page the ranking does not name, and one whose ranked page is
missing from disk.

- [x] **Step 2: Run the focused tests and confirm they fail**

Run: `uv run pytest tests/test_pgdp_profile_input.py tests/test_cli_profile_pgdp.py -q`

Expected: FAIL on the unknown option.

- [x] **Step 3: Implement the mode**

Add `--whole-book` to `profile-pgdp`. When set, enumerate every `*.png` directly under each ranked
project directory in sorted order and measure all of them. Pool estimates and fit templates over
every measured page. Emit only the pages the ranking named, so the report a later `align-pgdp` run
consumes still holds the fixed selection.

Record on each project how many pages were measured and how many were emitted, so a reader can see
the templates rest on more pages than the report lists.

- [x] **Step 4: Confirm the focused tests pass**

Run: `uv run pytest tests/test_pgdp_profile_input.py tests/test_cli_profile_pgdp.py -q`

Expected: PASS.

## Task 2: Measure first-band statistics per book

**Files:**

- Modify: `src/pdomain_ocr_synth/pgdp/profiling.py`
- Modify: `tests/test_pgdp_profiling.py`

- [x] **Step 1: Write failing tests for the book statistic**

Cover a book whose pages share a first-band position, one whose pages scatter, and one with a single
page. Assert the median first-band `y_start` and its median absolute deviation, and assert that
pages with no ink band are excluded from both.

- [x] **Step 2: Run the focused test and confirm it fails**

Run: `uv run pytest tests/test_pgdp_profiling.py -q`

Expected: FAIL on the missing statistic.

- [x] **Step 3: Implement the statistic**

Reuse the existing `median-mad/v1` method. Emit `first_band_top_px` and `first_band_mad_px` as
pooled book estimates alongside the current margins and band pitch.

Pool over every page Task 1 measured, not only the pages the report emits. A book statistic fitted
on five ranked pages is not a book statistic.

- [x] **Step 4: Confirm the focused test passes**

Run: `uv run pytest tests/test_pgdp_profiling.py -q`

Expected: PASS.

## Task 3: Fit book templates

**Files:**

- Create: `src/pdomain_ocr_synth/pgdp/page_templates.py`
- Create: `tests/test_pgdp_page_templates.py`

- [x] **Step 1: Write failing tests for template fitting**

Cover a book that splits cleanly into recto and verso by text-block left edge, one whose two sides
do not differ, and one whose deviation exceeds the limit. Assert that the third yields no templates.

Assert each template records its first-band `y_start`, text-block left and right edges, modal band
count, assigned page count, and share of the book.

- [x] **Step 2: Run the focused test and confirm it fails**

Run: `uv run pytest tests/test_pgdp_page_templates.py -q`

Expected: FAIL with `ModuleNotFoundError`.

- [x] **Step 3: Implement fitting**

Add `_HEAD_MAD_MAXIMUM_PX = 2`. A book with a larger first-band deviation yields no templates.

Split qualifying pages into recto and verso by text-block left edge, then fit a normal template to
each side.

Define the head window as the book's median first-band `y_start` plus or minus
`max(2, 3 x deviation)` px. That is the same tolerance a page uses to join a normal template, so one
bound governs both. Fit a chapter-opening template from pages with no band inside the head window
whose first band sits at least `_CHAPTER_SINK_MINIMUM_PX = 150` below the median.

- [x] **Step 4: Confirm the focused test passes**

Run: `uv run pytest tests/test_pgdp_page_templates.py -q`

Expected: PASS.

## Task 4: Classify each page

**Files:**

- Modify: `src/pdomain_ocr_synth/pgdp/page_templates.py`
- Modify: `tests/test_pgdp_page_templates.py`

- [x] **Step 1: Write failing tests for classification**

Cover one page per class: `normal_recto`, `normal_verso`, `chapter_opening`, and `unknown`. Assert
that a page whose offset lands between the head window and the chapter sink classifies `unknown`
rather than joining either template, and that every page of a book with no templates classifies
`unknown`.

Front matter and plates get no class of their own. Neither has a discriminator the corpus supports,
and both fall to `unknown`, which suppresses nothing.

Pin the two boundary cases the review found: a head 4px below its book median is still a head, and
genuine text 76px below is not.

Assert each page records `page_class` and `template_residual_px`.

- [x] **Step 2: Run the focused test and confirm it fails**

Run: `uv run pytest tests/test_pgdp_page_templates.py -q`

Expected: FAIL on the missing classifier.

- [x] **Step 3: Implement classification**

A page joins a normal template when its first-band residual is at most
`max(_HEAD_WINDOW_MINIMUM_PX, 3 x deviation)` px, with the minimum set to 8, and its text-block left
edge is within the same bound. Classify the trough between the head window and the chapter sink as
`unknown`.

Do not reuse the 2px figure from the book-steadiness test here. It measures how steady a book is,
not how far one page may sit from the median, and at 2px `p179.png` goes unclassified and stays
misaligned.

- [x] **Step 4: Confirm the focused test passes**

Run: `uv run pytest tests/test_pgdp_page_templates.py -q`

Expected: PASS.

## Task 5: Publish templates and classes as `pgdp-profile/v2`

**Files:**

- Modify: `src/pdomain_ocr_synth/pgdp/profile_models.py`
- Create: `schemas/pgdp-profile-v2.schema.json`
- Modify: `tests/test_pgdp_profile_models.py`

- [x] **Step 1: Write failing tests for the wire model**

Assert the report accepts `pgdp-profile/v2`, rejects an unknown major version, and carries templates
and page classes.

Version 1 is retained as its schema file and its git history, not as a readable payload. Assert that
`schemas/pgdp-profile-v1.schema.json` still exists and still names `pgdp-profile/v1`, and assert that
loading a version 1 payload raises. Rejecting an old major version is the M15b design's stated
behavior, so do not widen the wire `Literal` or relax the domain equality check.

- [x] **Step 2: Run the focused test and confirm it fails**

Run: `uv run pytest tests/test_pgdp_profile_models.py -q`

Expected: FAIL on the version strings.

- [x] **Step 3: Implement the version bump and regenerate the schema**

Bump the profile algorithm version, add the template and page-class fields, then write
`schemas/pgdp-profile-v2.schema.json` from the model.

- [x] **Step 4: Confirm the focused test passes**

Run: `uv run pytest tests/test_pgdp_profile_models.py -q`

Expected: PASS.

## Task 6: Suppress furniture bands in the extractor

**Files:**

- Modify: `src/pdomain_ocr_synth/pgdp/alignment_image.py`
- Modify: `src/pdomain_ocr_synth/pgdp/alignment.py`
- Modify: `tests/test_pgdp_alignment_image.py`

- [x] **Step 1: Write failing tests for suppression**

Cover a page listing a furniture band, asserting no candidate is emitted for it and a `running_head`
rejection records it. Cover a page listing none, asserting every band still yields a candidate.
Assert that `chapter_opening`, `front_matter`, `plate`, and `unknown` pages list no furniture band
and so behave exactly as they do today.

Assert the fragmented-band rate denominator excludes suppressed bands.

- [x] **Step 2: Run the focused test and confirm it fails**

Run: `uv run pytest tests/test_pgdp_alignment_image.py -q`

Expected: FAIL on the missing suppression.

- [x] **Step 3: Implement suppression**

Add `running_head` to the `RejectionReason` `Literal`.

The extractor is told which bands to drop rather than deriving it. Add a
`furniture_band_ordinals: Sequence[int] = ()` keyword parameter to `extract_line_candidates` at
`src/pdomain_ocr_synth/pgdp/alignment_image.py`, and pass `measurement.furniture_band_ordinals` from
`_align_profile_page` at `src/pdomain_ocr_synth/pgdp/alignment.py`. A listed band emits no candidate
and is recorded as a `running_head` rejection.

Task 4 computes the ordinals. A page classified `normal_recto` or `normal_verso` lists band 0 when
its `y_start` falls inside the head window, and lists nothing otherwise. A page classified
`chapter_opening`, `front_matter`, `plate`, or `unknown` lists nothing, so those pages behave exactly
as they do today.

- [x] **Step 4: Confirm the focused test passes**

Run: `uv run pytest tests/test_pgdp_alignment_image.py -q`

Expected: PASS.

## Task 7: Publish the extractor change as `pgdp-alignment/v3`

**Files:**

- Modify: `src/pdomain_ocr_synth/pgdp/alignment_models.py`
- Modify: `src/pdomain_ocr_synth/pgdp/alignment_image.py`
- Create: `schemas/pgdp-alignment-v3.schema.json`
- Modify: `tests/test_pgdp_alignment_models.py`
- Modify: `tests/test_cli_align_pgdp.py`

- [x] **Step 1: Write failing tests for the version strings**

Assert `pgdp-alignment/v3` and `source-frame-components/v3`, and that the serialized method block
records `head_mad_maximum_px` and `chapter_sink_minimum_px`.

As in Task 5, versions 1 and 2 are retained as schema files and git history. Assert both schema files
still exist and name their own versions, and assert that loading a version 1 or version 2 payload
raises.

- [x] **Step 2: Run the focused tests and confirm they fail**

Run: `uv run pytest tests/test_pgdp_alignment_models.py tests/test_cli_align_pgdp.py -q`

Expected: FAIL on the version strings.

- [x] **Step 3: Implement the version bump**

Bump both version strings, move the wire `Literal` to the new version, add the two constants to the
method block, and regenerate the v3 schema. Retain the v1 and v2 schema files unchanged.

- [x] **Step 4: Confirm the focused tests pass**

Run: `uv run pytest tests/test_pgdp_alignment_models.py tests/test_cli_align_pgdp.py -q`

Expected: PASS.

## Task 8: Rerun the fixed review and measure the gates

**Files:**

- Modify: `docs/plans/2026-08-31-pgdp-page-classification.md`

- [x] **Step 1: Reprofile the five review books whole**

Run `profile-pgdp --whole-book` against the fixed ranking. It measures every page of the five books
and emits the same 25, so `align-pgdp` runs unchanged against the fixed selection.

- [x] **Step 2: Confirm deterministic replay**

Run `align-pgdp` twice and confirm the reports are byte-identical.

- [x] **Step 3: Verify the known header steals are gone**

Expected: `p008.png` and `p179.png` no longer bind source line 0 to their running head. `118.png` and
`a005.png` still match their first band, because it is genuine text.

- [ ] **Step 4: Rebuild the confusion ledger and reconcile every page**

Render overlays for every eligible page, record the intended and observed mapping and a reviewer
decision per operation, and reconcile all 25 pages into exactly one of the four categories.

- [x] **Step 5: Measure the three gates**

Expected: at least 98 percent accepted-line precision, at least 30 accepted pages in every
admitted book,
zero accepted declared-complex pages.

- [x] **Step 6: Re-sweep the candidate box mode**

The dominant mode was chosen because union widened running-head bands into body-line shapes. With
heads suppressed that reason is gone, so rerun the six-variant sweep and record whether union now
wins.

- [x] **Step 7: Record the measured counts in this plan**

Write the exclusion counts, page reconciliation, ledger hash, and report hash into a
`## Corpus review result` section. Do not weaken a gate to make the review pass.

## Task 9: Update the documentation and context

**Files:**

- Modify: `docs/usage/recipe-workflow.md`
- Modify: `docs/context/current-state.md`
- Modify: `docs/context/intent-map.md`
- Modify: `docs/plans/README.md`

- [x] **Step 1: Document the wire versions and the page classes**

- [x] **Step 2: Record the measured counts, coverage, precision, and residual risks**

- [x] **Step 3: Mark milestones**

Mark this plan and the M15b plans `implemented` only if all three gates pass. Otherwise leave them
`partial` and state which gate failed.

## Task 10: Verify and commit

- [x] **Step 1: Run the full test suite**

Run: `make ci AI=1`

Expected: PASS with no new lint, type, test, or build failures.

- [x] **Step 2: Run the documentation gate**

Run: `docgraph reindex && docgraph check --strict && git diff --check`

Expected: no new blocking issue and `git diff --check` exits 0.

- [ ] **Step 3: Close the tracker**

Close `ConcaveTrillion/ocr-container-meta#403` only when all three gates pass.

- [x] **Step 4: Commit locally**

Do not push without explicit approval.

## Corpus review result

Running-head suppression works. Both gates still fail, and the milestone stays partial.

The fixed 25-page selection was reprofiled with `--whole-book`, pooling 1,367 pages to emit 25. Two
`align-pgdp` runs were byte-identical, with report SHA-256
`525c7604c944ceb4e794cbefdb62f0fba7cc78cd58d65fe0550f17568c401627` against profile SHA-256
`d7ea14ac83e35207c4d02b53b5b9ea5ba4964bf251d99976f495f2653d2782ae`.

Page reconciliation is unchanged at 13 eligible, 10 unavailable or malformed, 2 declared complex, and
0 source changed. Accepted pages rose from 5 to 7 and eligible-page coverage from 0.385 to 0.538. No
declared-complex page was accepted.

| stage | fragmented_band | accepted | coverage |
|---|---|---|---|
| version 1 | 23 | 0 | undefined |
| version 2 extractor | 5 | 3 | 0.231 |
| speck bands dropped | 5 | 5 | 0.385 |
| running heads suppressed | 5 | 6 | 0.462 |
| union candidate box | 5 | 7 | 0.538 |

The two pages that bound source line 0 to their running head are fixed. `p008.png` is no longer
accepted, and `p179.png` is accepted with its first source line on the first body row.

Every accepted page was checked at both ends of its monotone path against the source text. All 216
matches across the seven pages run in strictly increasing source and candidate order, and the first
and last match of each page carry the right text. No shifted page remains.

That check is not the confusion ledger the gate requires. It was read from the report and the
rendered overlays rather than signed off line by line by a person, so accepted-line precision stays
undefined and its gate stays failed. Overlays for all 13 eligible pages are in
`/workspaces/pdomain/.m15b-evidence/overlays-v3/`.

Coverage of 0.538 fell short of the 0.70 gate, and that gate has since been withdrawn. The five
eligible pages that remain unaccepted all fail on uniqueness margin, and four of them come from the
two books whose first-band deviation exceeds 2px, so they fit no templates and their heads were
never suppressed.

The 0.70 target was replaced on 2026-08-31 by per-book admission at 30 accepted pages, because
coverage was being measured on the review selection rather than on whole books. Whole-book runs
over all five books admit three of them, with 226, 75, and 52 accepted pages against 14 and 0 for
the two that are left out. See `docs/specs/2026-08-31-pgdp-whole-book-yield-gate-design.md`.

## Measured accepted-line precision, 2026-08-31

Precision is 0.9716, which is 615 correct matches of 633, against a 0.98 gate. The gate fails.

Every error falls on a page that carries no page class. Classified pages score 394 of 394, and
unclassified pages 221 of 239.

| book | pages reviewed | matches | precision |
|---|---|---|---|
| `projectID609bfa0449bdf` | 8 | 180 | 1.000 |
| `projectID64a479f51ce5b` | 6 | 242 | 1.000 |
| `projectID603d7d5e04ca0` | 5 | 137 | 0.891 |
| `projectID657550412c8dc` | 3 | 74 | 0.959 |

All 18 errors are the same defect. The running head becomes candidate 0 and takes a body source
line, which shifts the rows beneath it until a short source line absorbs the offset. That costs one
row on `098.png` and twelve on `089.png`.

The classified matches are not easy cases. They include small-capital address blocks, italic date
headings, accented words, currency and fractions, drama speaker labels, and hyphenated words joined
across a line end. None of them failed.

Requiring a page class before acceptance would raise precision on this sample to 1.000. Accepted
pages would fall from 367 to 306, and admitted books from three to two, keeping
`projectID609bfa0449bdf` at 226 pages and `projectID64a479f51ce5b` at 74.

Two limits apply to this measurement. The reviewer was a model reading rendered line crops against
each source line, not a person signing off each row, so it is evidence rather than the human
sign-off the gate names. And it covers four books, because the fifth accepts no pages at all, where
the plan asks for five.

Evidence: `.m15b-evidence/decisions.jsonl`, `.m15b-evidence/precision-v3.json`,
`.m15b-evidence/ledger-sheets/`, and the scripts `render_ledger_sheets.py`,
`select_precision_sample.py`, and `measure_precision.py`.

## After the template fitting fix, 2026-08-31

All three gates pass. Precision is 0.9974, which is 779 correct matches of 781; no declared-complex
page is accepted; and all five books clear the 30-page admission minimum, with 665 accepted pages
between them.

Two fitting defects were corrected. The binding-side split now groups pages by text-block left edge
rather than by the trailing digits of the file name, and the first-band deviation ceiling rose from
2px to 25px. Both are described in
[the page template design](../specs/2026-08-31-pgdp-whole-book-page-templates-design.md).

| book | classified before | after | accepted before | after | precision |
|---|---|---|---|---|---|
| `projectID609bfa0449bdf` | 300/312 | 300/312 | 226 | 226 | 1.000 |
| `projectID64a479f51ce5b` | 200/237 | 200/237 | 75 | 75 | 1.000 |
| `projectID603d7d5e04ca0` | 0/426 | 352/426 | 52 | 177 | 0.987 |
| `projectID657550412c8dc` | 27/312 | 250/312 | 14 | 155 | 1.000 |
| `projectID67a80fde44d34` | 0/98 | 63/98 | 0 | 32 | 1.000 |

The two healthy books are untouched. Their alignment reports differ only in `profile_label` and
`profile_sha256`, with zero pages changed, so their earlier ledger of 422 matches carries over.

Replay is deterministic. Re-profiling and re-aligning `projectID67a80fde44d34` reproduced a
byte-identical profile and page-identical alignment.

Two errors remain, both on `projectID603d7d5e04ca0` and both understood.

- `097.png` row 2 matches the source line `I.` to a decorative rule band. This is a separate defect
  from the running head and was present before the fix.
- `166.png` still classifies as `unknown`, so its running head is still matched to a body source
  line. Its first band sits outside the head window.

The ledger behind these numbers was reviewed by a model reading rendered line crops against each
source line, at the owner's direction, rather than signed off row by row by a person.

Evidence: `.m15b-evidence/precision-t2.json`, `.m15b-evidence/decisions-t2.jsonl`,
`.m15b-evidence/template-fix-comparison.txt`, and `.m15b-evidence/ledger-sheets-t2/`.

## Final review and handoff

Request a branch-wide review against the design and this plan. Resolve every accepted finding with a
focused test. Rerun `make ci AI=1`, the deterministic corpus replay, the visual precision ledger,
`docgraph check --strict`, and `git diff --check` before claiming completion.

The handoff must state that rectification, baselines, multi-column reading order, OCR verification,
adjacent-page context, and font fitting remain unimplemented.
