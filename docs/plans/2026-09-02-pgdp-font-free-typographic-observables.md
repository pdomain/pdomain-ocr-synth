---
Status: draft
Owner: CT
Created: 2026-09-02
Last verified: 2026-09-02
Kind: plan
---

# PGDP Font-Free Typographic Observables Implementation Plan

## Agent Index

- **Kind:** plan
- **Status:** draft
- **Owner:** CT
- **Created:** 2026-09-02
- **Last verified:** 2026-09-02
- **Provenance:** authored from the PGDP typography design, the shipped M15a/M15b implementation and wire contracts, the whole-book yield-gate design, and the 2026-09-02 handoff
- **Disposition:** Proposed executable plan for the next M15 slice. Not approved.
- **Read when:** implementing or reviewing scan-derived typographic measurement before any font candidate exists.
- **Search terms:** PGDP, M15, typography, x-height, baseline, word gap, stroke width, pooled book style, inverse rendering.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local `typography-pgdp` command that measures typographic observables from aligned ink and pools them into per-book, per-page-class styles, using no font candidates at all.

**Architecture:** Consume the shipped `pgdp-alignment/v3` report plus its `pgdp-profile/v2` profile. Rebuild the same page ink mask the alignment extractor built, measure per-line vertical extents, stroke weight, and word runs, then pool them in two robust stages. Write the evidence into a new `pgdp-typography/v1` report. Keep font candidates, inverse rendering, and rectification for later slices.

**Tech Stack:** Python 3.13, frozen dataclasses, Pydantic, Pillow, NumPy, argparse, pytest, Ruff, basedpyright, JSON Schema.

---

## Why this is the next slice

M15 says "Measure page geometry and typographic observables. Store uncertainty, provenance, source coordinates, and pooled book styles." Geometry shipped in M15a. Alignment shipped in M15b and now supplies a known transcription bound to a known ink box on 713 accepted pages across five books. Typographic observables and pooled book styles have never been started.

The design's target, inverse rendering that ranks font candidates by re-rendering a known transcription across size, feature, variation, tracking, blur, and ink-spread settings, is far too large for one plan. It also cannot be scored yet. Scoring a candidate render against observed ink requires knowing, per line, where the baseline sits, how tall the x-height is, how thick the strokes are, and how wide the word gaps run. None of that is measured today, so inverse rendering would be searching a space with no measured target.

This slice measures the target. Everything in it is font-free: it never opens a font file, never renders text, and never names a typeface.

## What is already measured, and what this adds

`pgdp-profile/v2` stores, per page: source frame, image mode, Otsu threshold, foreground pixel count, foreground bounds, four margins, half-open horizontal ink bands, `page_class`, `template_residual_px`, and `furniture_band_ordinals`. Its per-page derived estimates are `median_band_height_px` and `median_band_top_pitch_px`. Its pooled book estimates are the four margins, those two medians, and `first_band_top_px`, each with a `median_absolute_deviation` in `extensions`. `PageTemplateRecord` stores per-class `first_band_top_px`, `text_left_px`, `text_right_px`, `band_count`, `page_count`, and `page_share`.

That is page geometry. Every one of those numbers is measured over bands, which include running heads, folios, rules, and furniture, and none of them is bound to text.

`pgdp-alignment/v3` adds, per accepted page, match operations binding a `WireSourceLine` to a `WireLineCandidate` carrying a source-frame box, width, height, `component_count`, `foreground_pixels`, `fill_ratio`, and a width-length `horizontal_ink_profile` normalized to sum to 1.

That is where this slice starts. What it adds, all in the `source` frame and all in pixels:

| Observable | Where it comes from | Truth class |
|---|---|---|
| `baseline_row_px` | segment-wise vertical ink projection inside the matched box | derived |
| `x_height_px` | baseline row minus the sharpest upper rise in the same projection | derived |
| `ascender_extent_px`, `descender_extent_px` | box top and bottom relative to the baseline | derived |
| `line_ink_height_px`, `line_ink_width_px` | matched candidate box, already in the report | observed |
| `line_indent_px` | box left minus the page class's `text_left_px` | derived |
| `baseline_pitch_px` | consecutive matched baselines on one page | derived |
| `stroke_width_px` | median horizontal ink run between x-height top and baseline | derived |
| `word_gap_px` | zero-ink column runs in the stored profile, threshold from measured x-height | observed |
| `word_run_count` vs `source_word_count` | ink runs against the aligned transcription | observed |
| per-word ink box | one run plus its own row projection | observed |
| all of the above, pooled | two-stage median and MAD, per book and per `page_class` | pooled |

`baseline_pitch_px` is the one to contrast with what exists. M15a's `median_band_top_pitch_px` pools band tops including heads, folios, and rules. A baseline pitch measured between matched lines only, on accepted pages only, is the first leading-like observable in this repo that no furniture contaminates.

## Slice boundary

**In scope.** Reading an alignment report and its profile; rebuilding the page ink mask; per-line vertical extents, stroke width, skew slope, word runs and gaps, per-word boxes; two-stage pooling per book and page class; a new `pgdp-typography/v1` wire contract with a committed JSON Schema; a `typography-pgdp` CLI command; synthetic and reviewed fixtures; a corpus run with measured gates; and a sample-size calibration experiment.

**Explicitly out of scope.**

- Any font. No `fonts.py` import, no font file opened, no text rendered, no `make fetch-fonts`. Candidate ranking, inverse rendering, and typeface identity are a later slice.
- Any frame other than `source`. No rotation correction, dewarping, perspective, homography, or displacement grid.
- Any claim about the design's latent list. The report may not contain font identity, nominal point size, font advances, side bearings, native word-space width, tracking, pair kerning, leading in points, or physical margins. Task 4 enforces this with a denylist test.
- Any change to the emitted bytes of `pgdp-rank/v1`, `pgdp-profile/v2`, or `pgdp-alignment/v3`.
- Change-point detection over page index. The shipped `page_class` is the segmentation this slice uses.
- Changing `MINIMUM_ACCEPTED_PAGES_PER_BOOK`.
- Renderer, recipe, trainer-output, or shared-page-graph changes.
- Any LLM in the runtime path.

## Global Constraints

- Follow [the PGDP typography and structure synthesis design](../specs/2026-08-22-pgdp-typography-structure-synthesis-design.md).
- Preserve `pgdp-rank/v1`, `pgdp-profile/v2`, and `pgdp-alignment/v3` byte compatibility.
- Keep every coordinate in the `source` frame and every unit in `px`.
- Store `confidence: null` and `confidence_kind: "uncalibrated"` on every estimate.
- Treat PGDP text as fallible. Disagreement between transcription and ink is recorded as evidence, never a hard gate, and never drops an otherwise-good line measurement.
- Keep processing local, deterministic, snapshot-safe, and one image at a time.
- Run `make ci AI=1` before every implementation commit.

## How uncertainty is represented

`Estimate` in `profile_models.py` already exists for this and needs no change. Every reported value is an `Estimate` with `name`, `value`, `unit="px"`, a `truth_class`, `frame="source"`, a versioned `method`, `sample_count`, `evidence_pages`, `exclusions`, `confidence=None`, and `confidence_kind="uncalibrated"`. Dispersion goes in `extensions`, extending the idiom `profiling.pool_estimate` already uses: this slice adds `line_sample_count`, `excluded_line_count`, `percentile_16`, and `percentile_84`.

One constraint shapes the pooling design. `Estimate.__post_init__` requires `sample_count == len(evidence_pages)` and rejects duplicate pages. A book-level x-height pooled directly over roughly 21,000 lines would violate that, because samples would be lines and evidence would be pages.

Rather than relax a shipped invariant that currently catches bugs, pooling is two-stage: a robust median per page first, then pool page medians per book and page class. `sample_count` then equals the contributing page count by construction, and `extensions.line_sample_count` records the underlying line count. This is also statistically better, because it stops one dense page dominating a book.

## How the wire contract version changes

This slice adds a new report family, `pgdp-typography/v1`, with `schema_version: 1` and `algorithm_version: "pgdp-typography/v1"`. It does not extend the profile or alignment contracts.

That follows the design's rule and this repository's precedent. Version 1 readers reject unknown major versions but accept added optional fields. Here `schema_version` has stayed 1 while `algorithm_version` moved `pgdp-profile/v1` to `v2` and `pgdp-alignment/v1` to `v3`, with a committed schema file per algorithm version. Wire models use `extra="allow"` and round-trip unknown fields, which is how additive version-1 fields survive a rewrite.

So `schemas/pgdp-typography-v1.schema.json` is committed, the reader pins both literals, and unknown optional fields are preserved. When a later slice adds font candidates it becomes `pgdp-typography/v2` under the same `schema_version`. Only a change that breaks version-1 readers moves `schema_version` to 2, with fixture migrations.

Provenance is a hash chain. The typography report records `alignment_label` and `alignment_sha256`; the alignment report already records `profile_label` and `profile_sha256`. The command verifies the profile it is handed hashes to the alignment report's recorded value and refuses to run otherwise.

## Report size is a design constraint

Five books at 713 accepted pages and roughly 30 matched lines per page is about 21,000 lines, and on the order of 150,000 records at word granularity. Emitting every line and word would produce a report far larger than the product it carries.

The report therefore always emits per-book pooled estimates and per-page aggregates with counts and exclusions, and emits per-line and per-word rows only for a bounded, deterministic evidence sample: the first `--evidence-pages` accepted pages per book in natural page order, defaulting to 12. The pooled estimates are the product; the rows are for review and calibration. This mirrors M14's bounded review queue rather than inventing a new bounding rule.

## Tasks

### Task 1: Give both stages one definition of ink

**Files:** modify `src/pdomain_ocr_synth/pgdp/alignment_image.py`, modify `tests/test_pgdp_alignment_image.py`.

- [ ] Extract `_foreground_mask`, `_remove_page_borders`, and `_remove_long_rules` into one public `build_candidate_mask`, and have `extract_line_candidates` call it. No behaviour change; the diff should read as a move.
- [ ] Add the round-trip test: for every committed alignment fixture, cropping the mask to a candidate's box reproduces that candidate's recorded `foreground_pixels` and `horizontal_ink_profile` exactly.

This is provable rather than hopeful. `_extract_band_candidates` computes both values from `foreground[box]`, the page mask cropped to the cluster box, not from cluster membership, so a second stage rebuilding the same mask reproduces them bit for bit.

### Task 2: Measure vertical extents, stroke width, and skew per line

**Files:** create `src/pdomain_ocr_synth/pgdp/typography_measure.py`, create `tests/test_pgdp_typography_measure.py`.

- [ ] Estimate from a segment-wise vertical ink projection inside the matched box, splitting into column segments of `max(200, width // 8)` px, taking the median across segments and requiring at least three usable ones.
- [ ] Emit `skew_slope` per line, fitted over segment baselines, with a backstop exclusion above `|slope| > 0.02`.
- [ ] Derive `stroke_width_px` as the median horizontal ink run between the x-height top and the baseline.
- [ ] Test against committed synthetic block bitmaps with exactly known geometry.

Segmenting is what makes this work in an unrectified frame. A whole-line projection at 1500 px smears the baseline by 7.5 px at half a degree of skew, which destroys a 20 px x-height; a 200 px segment smears by 1.7 px. This is a local estimator, not a rectification.

### Task 3: Segment words and reconcile against the transcription

**Files:** modify `src/pdomain_ocr_synth/pgdp/typography_measure.py` and its test.

- [ ] Find word runs from the stored `horizontal_ink_profile`, treating zero-ink column runs of at least `max(2, round(0.25 * x_height_px))` as gaps. Deriving the threshold from measured x-height is why Task 2 lands first.
- [ ] Emit `word_run_count`, `source_word_count`, and `words_reconciled`. When counts agree, bind runs to words in order and emit per-word boxes and gap widths.
- [ ] When they disagree, still emit every line-level observable, emit no word rows, and record both counts.

The disagreement is evidence a later labeler or bbox-tightener pass needs, not a reason to discard a good line measurement.

### Task 4: Define the `pgdp-typography/v1` wire contract

**Files:** create `src/pdomain_ocr_synth/pgdp/typography_models.py`, create `schemas/pgdp-typography-v1.schema.json`, create `tests/test_pgdp_typography_models.py`, modify `src/pdomain_ocr_synth/pgdp/__init__.py`.

- [ ] Mirror `alignment_models.py`: frozen slotted dataclasses validating in `__post_init__`, paired wire models with `extra="allow"`, explicit `to_dict`, sorted-key deterministic JSON.
- [ ] Reuse `Estimate`, `CoordinateFrame`, and `ProfileDiagnostic` unchanged. Add `LineTypography`, `WordTypography`, `PageTypography`, `BookTypography`, and `TypographyReport`.
- [ ] Add the latent-discipline test: no emitted key matches the denylist, and every estimate carries `unit == "px"`, `frame == "source"`, `confidence is None`, and `confidence_kind == "uncalibrated"`.

This makes the design's latent list enforceable rather than aspirational.

### Task 5: Pool per book and per page class

**Files:** create `src/pdomain_ocr_synth/pgdp/typography_pooling.py` and its test.

- [ ] Two-stage median and MAD, page then book, grouped by the shipped `page_class`. Method version `typography-median-mad/v1`.
- [ ] Record exclusions as `"{page_name}:{code}"`, matching `profiling.pool_estimate`'s existing format.
- [ ] Pool `normal_recto` and `normal_verso` into the body style and `chapter_opening` separately. Report `unknown` counts but pool them into no style.
- [ ] State in the docstring that grouping by `page_class` is a cheaper stand-in for the design's change-point detection, and that title pages and notes are not separated by this slice.

### Task 6: Orchestrate and add `typography-pgdp`

**Files:** create `src/pdomain_ocr_synth/pgdp/typography.py`, create its tests and CLI test, modify `src/pdomain_ocr_synth/cli.py`, `tests/test_cli.py`, `tests/test_spec_docs.py`.

- [ ] `typography-pgdp CORPUS_ROOT --alignment PATH --profile PATH --output PATH [--evidence-pages N]`.
- [ ] Verify `sha256(profile) == alignment.profile_sha256` before doing any work.
- [ ] Reuse `open_image_snapshot`, the live-path rehash, and `write_report` exactly as `alignment.py` does. Return `VALIDATION_EXIT` and `DESTINATION_EXIT` as that command does. Print no JSON to stdout.
- [ ] Measure only accepted pages, recording proposed and excluded counts.
- [ ] On every measured page, verify the rebuilt mask reproduces each candidate's recorded values and that the rebuilt Otsu threshold equals the recorded one. On mismatch, exclude the page as `mask_mismatch` with both values as evidence.

### Task 7: Reviewed fixtures and a review overlay

**Files:** create `tests/fixtures/pgdp_typography/manifest.json` and its test, modify `src/pdomain_ocr_synth/pgdp/alignment_review.py`.

- [ ] Follow M15b's fixture rules including its licence rule: commit cropped or downsampled real scans only where the source licence permits, otherwise byte-stable synthetic derivatives, recording which is which.
- [ ] Add a review-only overlay drawing the estimated baseline and x-height on a matched line crop, outside the production report path.

### Task 8: Corpus run, gates, and the sample-size answer

**Files:** modify `docs/usage/recipe-workflow.md`, `docs/context/current-state.md`, `docs/plans/README.md`, and this plan.

- [ ] Run `typography-pgdp` twice over the five whole-book alignment reports and confirm `cmp` reports no difference.
- [ ] Measure every gate below and record the numbers whether they pass or fail.
- [ ] Run the calibration experiment: for each admitted book, deterministically subsample accepted body pages at n = 5, 10, 20, 30, 50, 100, recompute pooled x-height, baseline pitch, stroke width, and word gap at each n, and report the smallest n at which all four stop moving by more than 0.5 px.

## Acceptance gates

1. **Determinism.** Two runs over identical inputs produce byte-identical JSON; `cmp` exits 0.
2. **Mask reproduction.** Across all measured pages, 100.00 percent of matched candidates reproduce the recorded `foreground_pixels` and `horizontal_ink_profile` exactly, and every rebuilt Otsu threshold equals the recorded one. Zero `mask_mismatch` exclusions. A nonzero count means Task 1 is wrong and the slice stops.
3. **Synthetic estimator accuracy.** On at least 24 committed block fixtures spanning x-height 8 to 40 px, stroke 1 to 5 px, skew 0, plus and minus 0.5 and 1.0 degrees, and gaps 2 to 20 px, the estimator recovers baseline row within 1 px, x-height within 1 px, stroke width within 1 px, and the word-run count exactly, on 100 percent of fixtures.
4. **Reviewed line correctness.** At least 200 matched lines across at least three admitted books, rendered with baseline and x-height drawn: at least 0.95 judged correct, where correct means the baseline lies within 2 px of the visible baseline and the x-height line within 2 px of the lowercase top.
5. **Book-level stability.** For each admitted book, the MAD of per-page x-height medians is at most 0.08 times the book's pooled x-height. Pre-registered and uncalibrated.
6. **Word reconciliation floor.** At least 0.50 of measured lines per admitted book reconcile their ink-run count with their transcription word count. A sanity floor that catches a broken gap detector, not a claim that PGDP text agrees with the ink. A book below it is reported, not failed.
7. **Latent discipline.** The denylist and estimate-shape test passes on the real corpus report, not only on fixtures.
8. **Sample-size answer.** The Task 8 calibration number is measured and recorded for every admitted book.

Gates 5 and 6 carry pre-registered but uncalibrated numbers. Per the M15b rule, if either fails, record the exact counts, leave this plan `partial`, and open a follow-up. Do not weaken a gate inside the same review run.

## The 30-page admission minimum

The intent map says the 30-page seed cannot be calibrated until something downstream states how many pages a per-book typography fit needs, and names this plan as that consumer. The honest split:

**This slice can answer it for font-free observables, and Task 8 does.** Every observable here is a scalar pooled by a two-stage median, so its stability against page count is directly measurable from data this slice already produces. Stated before running so the measurement can contradict it: with per-page medians scattering by roughly 1 px and body pages carrying about 30 matched lines each, a book-level x-height should settle within 0.5 px somewhere around 10 to 15 pages, making 30 comfortably sufficient.

**This slice cannot answer it for font fitting.** That requirement depends on how the candidate space is parameterised, how many glyph instances per setting the scoring needs, and how many page classes must be fit separately. None of those exist, so any number offered now would be invented.

Recommendation: record the measured font-free number, leave `MINIMUM_ACCEPTED_PAGES_PER_BOOK` at 30, and state in `decisions.md` that the constant now has one calibrated lower bound and one still-open consumer.

## Fonts, and machines with no fonts fetched

This slice uses none. It imports nothing from `fonts.py`, opens no font file, renders no text, and never invokes `make fetch-fonts`. All eight gates are measurable on a bare checkout with no fonts present, because the estimator fixtures are synthetic block bitmaps rather than rendered type.

That is correct sequencing, not only convenience. Fonts land in `recipes/gaelic/fonts/`, which is gitignored, and the fetch script downloads six Gaelic families. The PGDP books this pipeline measures are English-language nineteenth and early-twentieth-century Latin-type volumes. The candidate set this repo can fetch today is the wrong script for the corpus it has measured, so building inverse rendering first would rank candidates that could not be right.

What this slice sets up but does not build, recorded so the later slice inherits it: a user-provided candidate-font manifest with per-font licence notes and no committed font bytes; a pytest marker so font-dependent tests skip cleanly where none are fetched; and a CLI that fails with an explicit "no candidate fonts configured" message rather than silently ranking an empty set.

## Open decisions

1. **Milestone name.** The M15b design reserves M15c for rectification, and this slice is not rectification. Suggest `15d` with a note, but the letter is yours.
2. **Measure in the source frame now, or rectify first?** The biggest one. The design says measurement starts by rectifying, and M15b defers baselines and x-height until after M15c. This plan measures in the source frame using segment-wise projection and treats skew as a reported observable. The argument for it: segmenting cuts skew smear by roughly an order of magnitude, the measured skew distribution is itself the evidence needed to scope rectification, and a rectification slice with no typographic target is hard to gate. This is a genuine departure from the spec's stated order.
3. **Mask-reading slice, or report-only slice?** A smaller version exists: consume only the alignment report, open no images, and ship word gaps, indentation, line ink height and width, and baseline pitch from stored values. It cannot produce x-height, ascender or descender extents, or stroke width, which need row projections the report does not store. Recommend the mask-reading version, because x-height is the observable the milestone is about.
4. **May Task 1 touch `alignment_image.py`?** The alternative duplicates the mask code and relies on Gate 2 to catch drift. Recommend the refactor.
5. **CLI name.** `typography-pgdp` matches the `rank-pgdp` / `profile-pgdp` / `align-pgdp` family. `measure-pgdp` reads better but collides conceptually with `profile-pgdp`.
6. **Are 0.08 and 0.50 acceptable as pre-registered seeds,** and does a failure block the slice or become a follow-up?
7. **Who reviews Gate 4?** Both prior M15b precision measurements were made by a model reading rendered crops, recorded as such. Same again, or a person this time?
8. **The default of 12 evidence pages per book.** Report size forces a bound; the number is a judgement call.

## Final review and handoff

Request a branch-wide review against the design and this plan. Resolve every accepted finding with a focused test. Rerun `make ci AI=1`, the deterministic corpus replay, the review ledger, `docgraph check --strict`, and `git diff --check` before claiming completion.

The handoff must state that font candidates, inverse rendering, typeface ranking, rectification, rectified frames, change-point detection, and any point-size or leading claim remain unimplemented.
