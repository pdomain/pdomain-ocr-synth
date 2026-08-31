# PGDP Page Classification Implementation Plan

## Agent Index

- **Kind:** plan
- **Status:** draft
- **Owner:** CT
- **Created:** 2026-08-31
- **Last verified:** 2026-08-31
- **Provenance:** derived from the approved whole-book page template design and first-band geometry
  measured across 41 whole PGDP books on 2026-08-31
- **Disposition:** Active executable plan for M15a page classification and furniture suppression.
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
- Do not change the three quality gates: 98 percent accepted-line precision, 70 percent
  eligible-page coverage, and zero accepted declared-complex pages.
- Do not change the alignment thresholds: 90 percent matched lines, cost at most 0.22, uniqueness
  margin at least 0.15.
- Keep the fixed 25-page selection fixed and replay deterministic.
- Add no OCR engine. Every measurement comes from ink-band geometry.
- Do not read adjacent pages. Templates are book-level statistics, and the extractor still decodes
  one scan at a time.
- Run `make ci AI=1` after focused checks and before every implementation commit.
- Preserve `.venv-container` intact during CI. Move it to a unique temporary directory, set only
  `UV_PROJECT_ENVIRONMENT` to `.venv`, and restore it afterward.

## Task 1: Measure first-band statistics per book

**Files:**

- Modify: `src/pdomain_ocr_synth/pgdp/profiling.py`
- Modify: `tests/test_pgdp_profiling.py`

- [ ] **Step 1: Write failing tests for the book statistic**

Cover a book whose pages share a first-band position, one whose pages scatter, and one with a single
page. Assert the median first-band `y_start` and its median absolute deviation, and assert that
pages with no ink band are excluded from both.

- [ ] **Step 2: Run the focused test and confirm it fails**

Run: `uv run pytest tests/test_pgdp_profiling.py -q`

Expected: FAIL on the missing statistic.

- [ ] **Step 3: Implement the statistic**

Reuse the existing `median-mad/v1` method. Emit `first_band_top_px` and `first_band_mad_px` as
pooled book estimates alongside the current margins and band pitch.

- [ ] **Step 4: Confirm the focused test passes**

Run: `uv run pytest tests/test_pgdp_profiling.py -q`

Expected: PASS.

## Task 2: Fit book templates

**Files:**

- Create: `src/pdomain_ocr_synth/pgdp/page_templates.py`
- Create: `tests/test_pgdp_page_templates.py`

- [ ] **Step 1: Write failing tests for template fitting**

Cover a book that splits cleanly into recto and verso by text-block left edge, one whose two sides
do not differ, and one whose deviation exceeds the limit. Assert that the third yields no templates.

Assert each template records its first-band `y_start`, text-block left and right edges, modal band
count, assigned page count, and share of the book.

- [ ] **Step 2: Run the focused test and confirm it fails**

Run: `uv run pytest tests/test_pgdp_page_templates.py -q`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement fitting**

Add `_HEAD_MAD_MAXIMUM_PX = 2`. A book with a larger first-band deviation yields no templates.

Split qualifying pages into recto and verso by text-block left edge, then fit a normal template to
each side. Fit a chapter-opening template from pages with no band in the head window whose first
band sits at least `_CHAPTER_SINK_MINIMUM_PX = 150` below the median.

- [ ] **Step 4: Confirm the focused test passes**

Run: `uv run pytest tests/test_pgdp_page_templates.py -q`

Expected: PASS.

## Task 3: Classify each page

**Files:**

- Modify: `src/pdomain_ocr_synth/pgdp/page_templates.py`
- Modify: `tests/test_pgdp_page_templates.py`

- [ ] **Step 1: Write failing tests for classification**

Cover one page per class: `normal_recto`, `normal_verso`, `chapter_opening`, `front_matter`,
`plate`, and `unknown`. Assert that a page whose offset lands between 11 and 149 pixels classifies
`unknown` rather than joining either template, and that every page of a book with no templates
classifies `unknown`.

Assert each page records `page_class` and `template_residual_px`.

- [ ] **Step 2: Run the focused test and confirm it fails**

Run: `uv run pytest tests/test_pgdp_page_templates.py -q`

Expected: FAIL on the missing classifier.

- [ ] **Step 3: Implement classification**

A page joins a normal template when its first-band residual is at most `max(2, 3 x deviation)` px
and its text-block left edge is within the same bound. Classify the trough between the head window
and the chapter sink as `unknown`.

- [ ] **Step 4: Confirm the focused test passes**

Run: `uv run pytest tests/test_pgdp_page_templates.py -q`

Expected: PASS.

## Task 4: Publish templates and classes as `pgdp-profile/v2`

**Files:**

- Modify: `src/pdomain_ocr_synth/pgdp/profile_models.py`
- Create: `schemas/pgdp-profile-v2.schema.json`
- Modify: `tests/test_pgdp_profile_models.py`

- [ ] **Step 1: Write failing tests for the wire model**

Assert the report accepts `pgdp-profile/v2`, rejects an unknown major version, and carries templates
and page classes. Assert a stored `pgdp-profile/v1` report still validates for replay, and that
`schemas/pgdp-profile-v1.schema.json` is retained unchanged.

- [ ] **Step 2: Run the focused test and confirm it fails**

Run: `uv run pytest tests/test_pgdp_profile_models.py -q`

Expected: FAIL on the version strings.

- [ ] **Step 3: Implement the version bump and regenerate the schema**

Bump the profile algorithm version, add the template and page-class fields, then write
`schemas/pgdp-profile-v2.schema.json` from the model.

- [ ] **Step 4: Confirm the focused test passes**

Run: `uv run pytest tests/test_pgdp_profile_models.py -q`

Expected: PASS.

## Task 5: Suppress furniture bands in the extractor

**Files:**

- Modify: `src/pdomain_ocr_synth/pgdp/alignment_image.py`
- Modify: `src/pdomain_ocr_synth/pgdp/alignment.py`
- Modify: `tests/test_pgdp_alignment_image.py`

- [ ] **Step 1: Write failing tests for suppression**

Cover a page whose class marks a head band, asserting no candidate is emitted for it and a
`running_head` rejection records it. Cover a `chapter_opening` page, asserting its first band is kept
because such pages carry no head. Cover an `unknown` page, asserting nothing is suppressed.

Assert the fragmented-band rate denominator excludes suppressed bands.

- [ ] **Step 2: Run the focused test and confirm it fails**

Run: `uv run pytest tests/test_pgdp_alignment_image.py -q`

Expected: FAIL on the missing suppression.

- [ ] **Step 3: Implement suppression**

Add `running_head` to the `RejectionReason` `Literal`. Suppress only bands the page class marks as
furniture, and only when the page's book produced templates.

- [ ] **Step 4: Confirm the focused test passes**

Run: `uv run pytest tests/test_pgdp_alignment_image.py -q`

Expected: PASS.

## Task 6: Publish the extractor change as `pgdp-alignment/v3`

**Files:**

- Modify: `src/pdomain_ocr_synth/pgdp/alignment_models.py`
- Modify: `src/pdomain_ocr_synth/pgdp/alignment_image.py`
- Create: `schemas/pgdp-alignment-v3.schema.json`
- Modify: `tests/test_pgdp_alignment_models.py`
- Modify: `tests/test_cli_align_pgdp.py`

- [ ] **Step 1: Write failing tests for the version strings**

Assert `pgdp-alignment/v3` and `source-frame-components/v3`, that the serialized method block records
`head_mad_maximum_px` and `chapter_sink_minimum_px`, and that v1 and v2 reports still validate.

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run: `uv run pytest tests/test_pgdp_alignment_models.py tests/test_cli_align_pgdp.py -q`

Expected: FAIL on the version strings.

- [ ] **Step 3: Implement the version bump**

Bump both version strings, widen the wire `Literal`, add the two constants to the method block, and
regenerate the v3 schema. Retain the v1 and v2 schema files.

- [ ] **Step 4: Confirm the focused tests pass**

Run: `uv run pytest tests/test_pgdp_alignment_models.py tests/test_cli_align_pgdp.py -q`

Expected: PASS.

## Task 7: Rerun the fixed review and measure the gates

**Files:**

- Modify: `docs/plans/2026-08-31-pgdp-page-classification.md`

- [ ] **Step 1: Reprofile the five review books whole**

Classification needs whole books. Profile all pages of the five books in the fixed selection, then
run `align-pgdp` against the same 25 pages.

- [ ] **Step 2: Confirm deterministic replay**

Run `align-pgdp` twice and confirm the reports are byte-identical.

- [ ] **Step 3: Verify the known header steals are gone**

Expected: `p008.png` and `p179.png` no longer bind source line 0 to their running head. `118.png` and
`a005.png` still match their first band, because it is genuine text.

- [ ] **Step 4: Rebuild the confusion ledger and reconcile every page**

Render overlays for every eligible page, record the intended and observed mapping and a reviewer
decision per operation, and reconcile all 25 pages into exactly one of the four categories.

- [ ] **Step 5: Measure the three gates**

Expected: at least 98 percent accepted-line precision, at least 70 percent eligible-page coverage,
zero accepted declared-complex pages.

- [ ] **Step 6: Re-sweep the candidate box mode**

The dominant mode was chosen because union widened running-head bands into body-line shapes. With
heads suppressed that reason is gone, so rerun the six-variant sweep and record whether union now
wins.

- [ ] **Step 7: Record the measured counts in this plan**

Write the exclusion counts, page reconciliation, ledger hash, and report hash into a
`## Corpus review result` section. Do not weaken a gate to make the review pass.

## Task 8: Update the documentation and context

**Files:**

- Modify: `docs/usage/recipe-workflow.md`
- Modify: `docs/context/current-state.md`
- Modify: `docs/context/intent-map.md`
- Modify: `docs/plans/README.md`

- [ ] **Step 1: Document the wire versions and the page classes**

- [ ] **Step 2: Record the measured counts, coverage, precision, and residual risks**

- [ ] **Step 3: Mark milestones**

Mark this plan and the M15b plans `implemented` only if all three gates pass. Otherwise leave them
`partial` and state which gate failed.

## Task 9: Verify and commit

- [ ] **Step 1: Run the full test suite**

Run: `make ci AI=1`

Expected: PASS with no new lint, type, test, or build failures.

- [ ] **Step 2: Run the documentation gate**

Run: `docgraph reindex && docgraph check --strict && git diff --check`

Expected: no new blocking issue and `git diff --check` exits 0.

- [ ] **Step 3: Close the tracker**

Close `ConcaveTrillion/ocr-container-meta#403` only when all three gates pass.

- [ ] **Step 4: Commit locally**

Do not push without explicit approval.

## Final review and handoff

Request a branch-wide review against the design and this plan. Resolve every accepted finding with a
focused test. Rerun `make ci AI=1`, the deterministic corpus replay, the visual precision ledger,
`docgraph check --strict`, and `git diff --check` before claiming completion.

The handoff must state that rectification, baselines, multi-column reading order, OCR verification,
adjacent-page context, and font fitting remain unimplemented.
