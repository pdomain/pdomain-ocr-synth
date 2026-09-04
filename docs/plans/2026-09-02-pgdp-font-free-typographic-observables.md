---
Status: complete
Owner: CT
Created: 2026-09-02
Last verified: 2026-09-04
Kind: plan
---

# PGDP Font-Free Typographic Observables Implementation Plan

## Agent Index

- **Kind:** plan
- **Status:** complete
- **Owner:** CT
- **Created:** 2026-09-02
- **Last verified:** 2026-09-04
- **Provenance:** authored from the PGDP typography design, the shipped M15a/M15b implementation and wire contracts, the
  whole-book yield-gate design, and the 2026-09-02 handoff
- **Disposition:** Complete as of 2026-09-04. All eight tasks landed and all eight gates pass.
  Gate 6 failed in two books under word segmentation v1 and passes in all five under v2, which
  derives the gap threshold from each book's own gap-length distribution.
- **Read when:** implementing or reviewing scan-derived typographic measurement before any font candidate exists.
- **Search terms:** PGDP, M15, typography, x-height, baseline, word gap, stroke width, pooled book style, inverse
  rendering.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
  superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local `typography-pgdp` command that measures typographic observables from aligned ink and pools them
into per-book, per-page-class styles, using no font candidates at all.

**Architecture:** Consume the shipped `pgdp-alignment/v3` report plus its `pgdp-profile/v2` profile. Rebuild the same
page ink mask the alignment extractor built, measure per-line vertical extents, stroke weight, and word runs, then pool
them in two robust stages. Write the evidence into a new `pgdp-typography/v1` report. Keep font candidates, inverse
rendering, and rectification for later slices.

**Tech Stack:** Python 3.13, frozen dataclasses, Pydantic, Pillow, NumPy, argparse, pytest, Ruff, basedpyright, JSON
Schema.

---

## Why this is the next slice

M15 says "Measure page geometry and typographic observables. Store uncertainty, provenance, source coordinates, and
pooled book styles." Geometry shipped in M15a. Alignment shipped in M15b and now supplies a known transcription bound to
a known ink box on 665 accepted pages across five books, measured on 2026-09-03 from the `alignment-t2-*`
reports. Typographic observables and pooled book styles have never been started.

The design's target, inverse rendering that ranks font candidates by re-rendering a known transcription across size,
feature, variation, tracking, blur, and ink-spread settings, is far too large for one plan. It also cannot be scored
yet. Scoring a candidate render against observed ink requires knowing, per line, where the baseline sits, how tall the
x-height is, how thick the strokes are, and how wide the word gaps run. None of that is measured today, so inverse
rendering would be searching a space with no measured target.

This slice measures the target. Everything in it is font-free: it never opens a font file, never renders text, and never
names a typeface.

## What is already measured, and what this adds

`pgdp-profile/v2` stores, per page: source frame, image mode, Otsu threshold, foreground pixel count, foreground bounds,
four margins, half-open horizontal ink bands, `page_class`, `template_residual_px`, and `furniture_band_ordinals`. Its
per-page derived estimates are `median_band_height_px` and `median_band_top_pitch_px`. Its pooled book estimates are the
four margins, those two medians, and `first_band_top_px`, each with a `median_absolute_deviation` in `extensions`.
`PageTemplateRecord` stores per-class `first_band_top_px`, `text_left_px`, `text_right_px`, `band_count`, `page_count`,
and `page_share`.

That is page geometry. Every one of those numbers is measured over bands, which include running heads, folios, rules,
and furniture, and none of them is bound to text.

`pgdp-alignment/v3` adds, per accepted page, match operations binding a `WireSourceLine` to a `WireLineCandidate`
carrying a source-frame box, width, height, `component_count`, `foreground_pixels`, `fill_ratio`, and a width-length
`horizontal_ink_profile` normalized to sum to 1.

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

`baseline_pitch_px` is the one to contrast with what exists. M15a's `median_band_top_pitch_px` pools band tops including
heads, folios, and rules. A baseline pitch measured between matched lines only, on accepted pages only, is the first
leading-like observable in this repo that no furniture contaminates.

## Slice boundary

**In scope.** Reading an alignment report and its profile; rebuilding the page ink mask; per-line vertical extents,
stroke width, skew slope, word runs and gaps, per-word boxes; two-stage pooling per book and page class; a new
`pgdp-typography/v1` wire contract with a committed JSON Schema; a `typography-pgdp` CLI command; synthetic and reviewed
fixtures; a corpus run with measured gates; and a sample-size calibration experiment.

**Explicitly out of scope.**

- Any font. No `fonts.py` import, no font file opened, no text rendered, no `make fetch-fonts`. Candidate ranking,
  inverse rendering, and typeface identity are a later slice.
- Any frame other than `source`. No rotation correction, dewarping, perspective, homography, or displacement grid.
- Any claim about the design's latent list. The report may not contain font identity, nominal point size, font advances,
  side bearings, native word-space width, tracking, pair kerning, leading in points, or physical margins. Task 4
  enforces this with a denylist test.
- Any change to the emitted bytes of `pgdp-rank/v1`, `pgdp-profile/v2`, or `pgdp-alignment/v3`.
- Change-point detection over page index. The shipped `page_class` is the segmentation this slice uses.
- Changing `MINIMUM_ACCEPTED_PAGES_PER_BOOK`.
- Renderer, recipe, trainer-output, or shared-page-graph changes.
- Any LLM in the runtime path.

## Global Constraints

- Follow [the PGDP typography and structure synthesis
  design](../specs/2026-08-22-pgdp-typography-structure-synthesis-design.md).
- Preserve `pgdp-rank/v1`, `pgdp-profile/v2`, and `pgdp-alignment/v3` byte compatibility.
- Keep every coordinate in the `source` frame and every unit in `px`.
- Store `confidence: null` and `confidence_kind: "uncalibrated"` on every estimate.
- Treat PGDP text as fallible. Disagreement between transcription and ink is recorded as evidence, never a hard gate,
  and never drops an otherwise-good line measurement.
- Keep processing local, deterministic, snapshot-safe, and one image at a time.
- Run `make ci AI=1` before every implementation commit.

## How uncertainty is represented

`Estimate` in `profile_models.py` already exists for this and needs no change. Every reported value is an `Estimate`
with `name`, `value`, `unit="px"`, a `truth_class`, `frame="source"`, a versioned `method`, `sample_count`,
`evidence_pages`, `exclusions`, `confidence=None`, and `confidence_kind="uncalibrated"`. Dispersion goes in
`extensions`, extending the idiom `profiling.pool_estimate` already uses: this slice adds `line_sample_count`,
`excluded_line_count`, `percentile_16`, and `percentile_84`.

One constraint shapes the pooling design. `Estimate.__post_init__` requires `sample_count == len(evidence_pages)` and
rejects duplicate pages. A book-level x-height pooled directly over roughly 21,000 lines would violate that, because
samples would be lines and evidence would be pages.

Rather than relax a shipped invariant that currently catches bugs, pooling is two-stage: a robust median per page first,
then pool page medians per book and page class. `sample_count` then equals the contributing page count by construction,
and `extensions.line_sample_count` records the underlying line count. This is also statistically better, because it
stops one dense page dominating a book.

## How the wire contract version changes

This slice adds a new report family, `pgdp-typography/v1`, with `schema_version: 1` and `algorithm_version:
"pgdp-typography/v1"`. It does not extend the profile or alignment contracts.

That follows the design's rule and this repository's precedent. Version 1 readers reject unknown major versions but
accept added optional fields. Here `schema_version` has stayed 1 while `algorithm_version` moved `pgdp-profile/v1` to
`v2` and `pgdp-alignment/v1` to `v3`, with a committed schema file per algorithm version. Wire models use
`extra="allow"` and round-trip unknown fields, which is how additive version-1 fields survive a rewrite.

So `schemas/pgdp-typography-v1.schema.json` is committed, the reader pins both literals, and unknown optional fields are
preserved. When a later slice adds font candidates it becomes `pgdp-typography/v2` under the same `schema_version`. Only
a change that breaks version-1 readers moves `schema_version` to 2, with fixture migrations.

Provenance is a hash chain. The typography report records `alignment_label` and `alignment_sha256`; the alignment report
already records `profile_label` and `profile_sha256`. The command verifies the profile it is handed hashes to the
alignment report's recorded value and refuses to run otherwise.

## Report size is a design constraint

Five books at 713 accepted pages and roughly 30 matched lines per page is about 21,000 lines, and on the order of
150,000 records at word granularity. Emitting every line and word would produce a report far larger than the product it
carries.

The report therefore always emits per-book pooled estimates and per-page aggregates with counts and exclusions, and
emits per-line and per-word rows only for a bounded, deterministic evidence sample: the first `--evidence-pages`
accepted pages per book in natural page order, defaulting to 12. The pooled estimates are the product; the rows are for
review and calibration. This mirrors M14's bounded review queue rather than inventing a new bounding rule.

## Tasks

### Task 1: Give both stages one definition of ink

**Files:** modify `src/pdomain_ocr_synth/pgdp/alignment_image.py`, modify `tests/test_pgdp_alignment_image.py`.

- [x] Extract `_foreground_mask`, `_remove_page_borders`, and `_remove_long_rules` into one public
      `build_candidate_mask`, and have `extract_line_candidates` call it. No behaviour change; the diff should read as a
      move.
- [x] Add the round-trip test: for every committed alignment fixture, cropping the mask to a candidate's box reproduces
      that candidate's recorded `foreground_pixels` and `horizontal_ink_profile` exactly.

This is provable rather than hopeful. `_extract_band_candidates` computes both values from `foreground[box]`, the page
mask cropped to the cluster box, not from cluster membership, so a second stage rebuilding the same mask reproduces them
bit for bit.

### Task 2: Measure vertical extents, stroke width, and skew per line

**Files:** create `src/pdomain_ocr_synth/pgdp/typography_measure.py`, create `tests/test_pgdp_typography_measure.py`.

- [x] Estimate from a segment-wise vertical ink projection inside the matched box, splitting into column segments of
      `max(200, width // 8)` px, taking the median across segments and requiring at least three usable ones.
- [x] Emit `skew_slope` per line, fitted over segment baselines, with a backstop exclusion above `|slope| > 0.02`.
- [x] Derive `stroke_width_px` as the median horizontal ink run between the x-height top and the baseline.
- [x] Test against committed synthetic block bitmaps with exactly known geometry.

Segmenting is what makes this work in an unrectified frame. Smear across a width `w` at skew angle `t` is `w * tan(t)`.
At half a degree, a whole-line projection 1500 px wide smears the baseline by 13.1 px, which destroys a 20 px x-height.
A 200 px segment smears by 1.75 px. The reduction is the width ratio, 7.5 times. This is a local estimator, not a
rectification.

### Task 3: Segment words and reconcile against the transcription

**Files:** modify `src/pdomain_ocr_synth/pgdp/typography_measure.py` and its test.

- [x] Find word runs from the stored `horizontal_ink_profile`, treating zero-ink column runs of at least `max(2,
      round(0.25 * x_height_px))` as gaps. Deriving the threshold from measured x-height is why Task 2 lands first.
- [x] Emit `word_run_count`, `source_word_count`, and `words_reconciled`. When counts agree, bind runs to words in order
      and emit per-word boxes and gap widths.
- [x] When they disagree, still emit every line-level observable, emit no word rows, and record both counts.

The disagreement is evidence a later labeler or bbox-tightener pass needs, not a reason to discard a good line
measurement.

### Task 4: Define the `pgdp-typography/v1` wire contract

**Files:** create `src/pdomain_ocr_synth/pgdp/typography_models.py`, create `schemas/pgdp-typography-v1.schema.json`,
create `tests/test_pgdp_typography_models.py`, modify `src/pdomain_ocr_synth/pgdp/__init__.py`.

- [x] Mirror `alignment_models.py`: frozen slotted dataclasses validating in `__post_init__`, paired wire models with
      `extra="allow"`, explicit `to_dict`, sorted-key deterministic JSON.
- [x] Reuse `Estimate`, `CoordinateFrame`, and `ProfileDiagnostic` unchanged. Add `LineTypography`, `WordTypography`,
      `PageTypography`, `BookTypography`, and `TypographyReport`.
- [x] Add the latent-discipline test: no emitted key matches the denylist, and every estimate carries `unit == "px"`,
      `frame == "source"`, `confidence is None`, and `confidence_kind == "uncalibrated"`.

This makes the design's latent list enforceable rather than aspirational.

### Task 5: Pool per book and per page class

**Files:** create `src/pdomain_ocr_synth/pgdp/typography_pooling.py` and its test.

- [x] Two-stage median and MAD, page then book, grouped by the shipped `page_class`. Method version
      `typography-median-mad/v1`.
- [x] Record exclusions as `"{page_name}:{code}"`, matching `profiling.pool_estimate`'s existing format.
- [x] Pool `normal_recto` and `normal_verso` into the body style and `chapter_opening` separately. Report `unknown`
      counts but pool them into no style.
- [x] State in the docstring that grouping by `page_class` is a cheaper stand-in for the design's change-point
      detection, and that title pages and notes are not separated by this slice.

### Task 6: Orchestrate and add `typography-pgdp`

**Files:** create `src/pdomain_ocr_synth/pgdp/typography.py`, create its tests and CLI test, modify
`src/pdomain_ocr_synth/cli.py`, `tests/test_cli.py`, `tests/test_spec_docs.py`.

- [x] `typography-pgdp CORPUS_ROOT --alignment PATH --profile PATH --output PATH [--evidence-pages N]`.
- [x] Verify `sha256(profile) == alignment.profile_sha256` before doing any work.
- [x] Reuse `open_image_snapshot`, the live-path rehash, and `write_report` exactly as `alignment.py` does. Return
      `VALIDATION_EXIT` and `DESTINATION_EXIT` as that command does. Print no JSON to stdout.
- [x] Measure only accepted pages, recording proposed and excluded counts.
- [x] On every measured page, verify the rebuilt mask reproduces each candidate's recorded values and that the rebuilt
      Otsu threshold equals the recorded one. On mismatch, exclude the page as `mask_mismatch` with both values as
      evidence.

### Task 7: Reviewed fixtures and a review overlay

**Files:** create `tests/fixtures/pgdp_typography/manifest.json` and its test, modify
`src/pdomain_ocr_synth/pgdp/alignment_review.py`.

- [x] Follow M15b's fixture rules including its licence rule: commit cropped or downsampled real scans only where the
      source licence permits, otherwise byte-stable synthetic derivatives, recording which is which.
- [x] Add a review-only overlay drawing the estimated baseline and x-height on a matched line crop, outside the
      production report path.

### Task 8: Corpus run, gates, and the sample-size answer

**Files:** modify `docs/usage/recipe-workflow.md`, `docs/context/current-state.md`, `docs/plans/README.md`, and this
plan.

- [x] Run `typography-pgdp` twice over the five whole-book alignment reports and confirm `cmp` reports no difference.
- [x] Measure every gate below and record the numbers whether they pass or fail.
- [x] Run the calibration experiment: for each admitted book, deterministically subsample accepted body pages at n = 5,
      10, 20, 30, 50, 100, recompute pooled x-height, baseline pitch, stroke width, and word gap at each n, and report
      the smallest n at which all four stop moving by more than 0.5 px.
- [x] Truncate the sweep per book at that book's own accepted body-page count, and report the truncation. Not every
      admitted book reaches n = 100. The 2026-08-31 per-book accepted counts were 226, 75, 177, 155, and 32, so at least
      one book cannot reach even n = 50. A book whose sweep truncates before its four observables settle reports "did
      not converge within available pages" rather than a number, and that outcome is itself the answer for that book.

## Measured on 2026-09-03: the segment floor excludes 13.9 percent of lines

Task 2's estimator needs at least three segments of `max(200, width // 8)` px, so a matched line
narrower than 600 px is excluded as `insufficient_segments`. Measured against the five whole-book
alignment reports in `.m15b-evidence/`, over 9,754 matched lines on 367 accepted pages:

| width | share of matched lines |
| --- | ---: |
| under 400 px | 9.3 percent |
| under 600 px | 13.9 percent |
| under 800 px | 64.1 percent |

Median width is 784 px and the tenth percentile is 431 px. The widest excluded line is 599 px,
confirming the cliff sits exactly at three segments.

Losing 13.9 percent of lines costs the pooled estimates little, because pooling is two-stage and a
page with thirty matched lines still contributes a solid median after losing four. The exclusions
are not random, though: short lines are paragraph-final lines, headings, and verse, so the loss is
biased rather than uniform.

**One consequence is a correctness problem, not a coverage one.** `baseline_pitch_px` is defined
above as the distance between consecutive matched baselines on a page. When one line in a run has
no baseline, the next available pair is two lines apart, and measuring it as a pitch silently
reports roughly double the true leading. Task 3 or Task 5 must define what consecutive means in the
presence of exclusions. The options are to emit a pitch only for adjacent matched lines whose
ordinals differ by one, or to record the ordinal gap alongside each pitch and let pooling divide by
it. Emitting only adjacent pairs is simpler and loses nothing that matters, since a page has many
pairs.

## Measured on 2026-09-03: what word reconciliation can reach

Gate 6's 0.50 floor was a reasoned seed. Measured against 9,682 matched lines from the five
whole-book reports, using the stored `horizontal_ink_profile` and the aligned `visible_text` and
sweeping an absolute gap threshold independent of any x-height estimate:

| gap threshold | exact | over-split | under-split |
| --- | ---: | ---: | ---: |
| 4 px | 0.611 | 0.379 | 0.010 |
| 5 px | 0.703 | 0.281 | 0.016 |
| 6 px | 0.718 | 0.242 | 0.040 |
| 7 px | 0.709 | 0.215 | 0.075 |
| 8 px | 0.676 | 0.188 | 0.135 |

Three things follow.

The detector tops out near 0.72, so roughly 28 percent of lines will not reconcile even at the best
threshold. **Superseded on 2026-09-03.** That ceiling is an artifact of sweeping one absolute
threshold across all five books pooled, which averages over books whose optima differ from 5 to
11 px. Measured per book, the detector reaches 0.63 to 0.84, and a per-page threshold derived from
the page's own gap distribution reaches 0.61 to 0.81. See
[the word-gap threshold finding](../research/2026-09-03-word-gap-threshold-is-too-low.md).

Word-count disagreement is still normal rather than a defect, which supports the plan's decision to
keep every line-level observable when counts disagree instead of dropping the line. Gate 6 at 0.50
is achievable with real headroom, not a coin flip.

The curve is flat between 5 and 8 px, so the threshold does not need to be precise. At a typical
20 px x-height, `max(2, round(0.25 * x_height_px))` gives 5 px, which sits inside that plateau. The
0.25 coefficient looks right.

The rate is sensitive to the x-height estimate, not to the coefficient. Substituting a crude proxy
of a fixed fraction of ink height gives 0.135 at 0.35, 0.514 at 0.45, and 0.662 at 0.55, because
ink height varies with whether a line happens to carry ascenders or descenders. Task 2 measures
x-height directly per line rather than as a fraction, so it should beat the proxy. Treat 0.72 as the
target and the proxy figures as a floor, and confirm the real number in Task 8 rather than assuming
it.

## Measured on 2026-09-03: the corpus run and every gate

The five whole-book runs used the `alignment-t2-*` reports and their `profile-t2-*` profiles
in `/workspaces/pdomain/.m15b-evidence/`, not the older `alignment-wholebook-*` pair. Only the
t2 set carries the page-classification fixes, and only it matches the per-book accepted counts
this plan already quotes: 226, 75, 177, 155, and 32, for 665 accepted pages. The older
whole-book reports accept 367 pages and class one whole book `unknown`, and the two earlier
"Measured on 2026-09-03" sections above were taken from them. Their conclusions still hold
because they measure line widths and gap thresholds rather than page counts.

Every gate below was measured on the t2 corpus report. Evidence lives in
`/workspaces/pdomain/.m15d-evidence/`.

| Gate | Result | Verdict |
| --- | --- | ---: |
| 1. Determinism | 5 of 5 books byte-identical across two runs | pass |
| 2. Mask reproduction | 665 measured pages, 17,205 matched candidates verified, 0 `mask_mismatch` | pass |
| 3. Synthetic estimator | 34 of 34 fixtures within 1 px, plus 8 reviewed fixtures | pass |
| 4. Reviewed line correctness | 208 of 210 judged correct, 0 incorrect | pass |
| 5. Book-level stability | relative MAD 0.000 in all 5 books, ceiling 0.08 | pass |
| 6. Word reconciliation | 0.620, 0.539, 0.520 pass; 0.476 and 0.208 fail | 3 of 5, fixed below |
| 7. Latent discipline | 0 violations across all 5 corpus reports | pass |
| 8. Sample-size answer | measured per book, below | pass |

**Gate 2 is the one that had to be exact, and is.** Across 665 pages, every one of 17,205
matched candidates reproduced its recorded `foreground_pixels` and `horizontal_ink_profile`
from the rebuilt mask, and every rebuilt Otsu threshold equalled the recorded one. Task 1's
claim that the two stages share one definition of ink holds on the whole corpus, not only on
fixtures.

**Gate 4 was model-reviewed, as decision 7 settled.** 210 matched lines from three books were
rendered by `render_line_typography_overlay` at 3x on a 460 px window, ten to a sheet, and
read. 208 were correct: the baseline lay on the visible baseline and the x-height rule on the
lowercase tops. None was wrong. The remaining two are all-capital and small-capital lines that
carry no lowercase at all, so the "within 2 px of the lowercase top" half of the criterion has
nothing to measure against; both baselines were correct. Counting those two as failures gives
0.9905, which clears the 0.95 threshold without needing the charitable reading.

**Gate 5 passes with room that looks suspicious and is not.** The MAD of per-page x-height
medians is exactly 0 in all five books. Per-page medians are integers, and a page of body text
at one type size produces the same integer median page after page, so the dispersion collapses
to zero. The 16th and 84th percentiles in `extensions` confirm the estimates are not
degenerate: they sit within 1 px of the median rather than on top of it.

**Gate 6 fails in two books and is recorded rather than weakened,** per decision 6.

| book | reconciled / measured lines | rate |
| --- | ---: | ---: |
| projectID609bfa0449bdf | 2801 / 4515 | 0.620 |
| projectID64a479f51ce5b | 1547 / 2868 | 0.539 |
| projectID67a80fde44d34 | 397 / 763 | 0.520 |
| projectID603d7d5e04ca0 | 1692 / 3553 | 0.476 |
| projectID657550412c8dc | 739 / 3546 | 0.208 |

The three passing books sit near the 0.72 ceiling the earlier sweep predicted. The two failing
books do not, and the gap is not uniform: projectID657550412c8dc reconciles one line in five.
Its measured word gap is 25 px against a 4 to 5 px gap threshold derived from its 18 px
x-height, which is the widest spacing in the corpus, so the detector is not under-splitting.
Over-splitting on wide inter-letter spacing is the likelier cause, and the follow-up should
measure the split direction per book before changing the threshold. **Follow-up required:**
measure over-split against under-split counts per book for the two failing books, and decide
whether the gap threshold needs a per-book term. This plan stayed `partial` until that landed;
it landed on 2026-09-04 and is measured below.

**That follow-up ran on 2026-09-03 and found the cause.** The shipped threshold,
`max(2, round(0.25 * x_height_px))`, is below the optimum in all five books, by 1 px at best and
6 px at worst, so it splits inside words at ordinary letter gaps. See
[the word-gap threshold finding](../research/2026-09-03-word-gap-threshold-is-too-low.md).

## Measured on 2026-09-04: Gate 6 passes in all five books under word segmentation v2

Word segmentation moved to `ink-profile-word-runs/v2`, which derives one gap threshold per book
by Otsu over the book's own pooled gap-length histogram, and the corpus was re-run. Gate 6 now
passes everywhere.

| book | gap threshold | reconciled / measured | v2 rate | v1 rate |
| --- | ---: | ---: | ---: | ---: |
| projectID609bfa0449bdf | 10 px | 3636 / 4515 | 0.805 | 0.620 |
| projectID64a479f51ce5b | 6 px | 2129 / 2868 | 0.742 | 0.539 |
| projectID603d7d5e04ca0 | 8 px | 2107 / 3553 | 0.593 | 0.476 |
| projectID657550412c8dc | 15 px | 2838 / 3546 | 0.800 | 0.208 |
| projectID67a80fde44d34 | 9 px | 597 / 763 | 0.782 | 0.520 |

**Gates 1 through 5, 7 and 8 came back unchanged, which is the check that the edit stayed inside
word segmentation.** Both passes are still byte-identical in all five books. Gate 2 still verifies
17,205 matched candidates across 665 pages with zero `mask_mismatch`. Gate 5's relative MAD is
still exactly 0.000 in every book, and every pooled x-height is the same integer as before. Gate 4
was not re-reviewed and did not need to be: re-rendering all 21 review sheets from the v2 reports
produced files byte-identical to the ones the 208-of-210 verdict was given on, because the overlay
draws the line box, the baseline, and the x-height rule and no word boxes. Gate 3 passes on the
regenerated fixtures.

**The book-level threshold is what ships, and per-page was measured against it rather than
assumed.** Book-level scores 0.811, 0.741, 0.620, 0.803, 0.783 over every matched line with a
profile; per-page scores 0.802, 0.751, 0.608, 0.814, 0.790 on the same lines. Book-level wins in
three books, per-page in two, and every difference is under 1.1 points. This corrects the research
finding's conclusion that the fix had to be per-page. Per-page values are recorded in each page's
`extensions` as evidence, and their within-book range is 4 to 12, 4 to 7, 4 to 10, 6 to 19, and 8
to 10 px.

**Otsu assumes two populations, so the split is checked before it is used.** The count at the
threshold must fall to at most half the smaller class peak. Otsu's own separability was tried
first and rejected: it scores 0.65 to 0.75 on a uniform, a single Gaussian, and a geometric decay
against 0.83 to 0.85 on the real books, so it does not tell the two cases apart. Valley depth
does, scoring 0.104 to 0.152 on the books and 1.00 to 1.18 on the same synthetic shapes. The guard
fired on no book and on 14 of 665 pages, all of them evidence-only.

**What is left is the residual disagreement, not the threshold.** Over the evidence-sampled pages,
which carry per-line rows, the surviving disagreement is mostly over-split in four books and
mostly under-split in projectID657550412c8dc. Exact agreement with a fallible F2 word count is not
the right long-run target, and the residual has not been attributed to a cause.

**Gate 8's word-gap answer improved and the other three did not move.** Word gap now settles in
every book, at 5, 50, 5, 30, and 5 body pages, where under v1 one book did not converge within 100
pages. x-height, baseline pitch, and stroke width settle at exactly the same page counts as
before, which is the same evidence that the geometry estimator is untouched.

An earlier hypothesis, that [F2's silent rejoining of line-break
hyphens](../research/2026-09-03-pgdp-f2-line-break-hyphens.md) drove the over-split, was tested and
failed both of its predictions. The F2 measurement stands; its attributed effect does not.

**Gate 8, the sample-size answer.** Body pages were shuffled with a fixed seed and pooled at
n = 5, 10, 20, 30, 50, 100, truncated at each book's own body-page count, and compared against
the full-book value at a 0.5 px tolerance.

| book | body pages | sweep | x-height | pitch | stroke | word gap | all four |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| projectID609bfa0449bdf | 212 | to 100 | 20 | 5 | 5 | did not converge | did not converge |
| projectID64a479f51ce5b | 71 | to 50 | 5 | 5 | 5 | 5 | 5 |
| projectID603d7d5e04ca0 | 168 | to 100 | 5 | 5 | 5 | 5 | 5 |
| projectID657550412c8dc | 149 | to 100 | 5 | 5 | 5 | 50 | 50 |
| projectID67a80fde44d34 | 32 | to 30 | 5 | 5 | 5 | 20 | 20 |

Two books truncate below n = 100 and one below n = 50, as the plan expected. Four of the five
converge, at 5, 5, 50, and 20 body pages. The fifth does not: projectID609bfa0449bdf's word gap
still sits 0.75 px from its full-book value at n = 100, so its answer is "did not converge
within available pages" for that observable, and 20 pages for the other three.

**What this says about the 30-page minimum.** For x-height, baseline pitch, and stroke width,
five body pages are enough in every book and twenty in the worst, so 30 is comfortably
sufficient and the prediction stated before the run was right. Word gap is the unstable
observable: one book needs 50 pages and another does not settle within 100. The honest
recommendation is unchanged. Leave `MINIMUM_ACCEPTED_PAGES_PER_BOOK` at 30, record that it now
has one calibrated lower bound for three of the four font-free observables, and note that word
gap and font fitting both remain uncalibrated consumers.

**One design correction the corpus forced.** Book-level estimates originally pooled only pages
belonging to a style. Measured against the older whole-book reports, one book classed all 52 of
its accepted pages `unknown` and reported no estimates at all despite carrying 902 measured
lines. Book estimates now pool every measured page and only styles stay class-gated.

## Acceptance gates

1. **Determinism.** Two runs over identical inputs produce byte-identical JSON; `cmp` exits 0.
2. **Mask reproduction.** Across all measured pages, 100.00 percent of matched candidates reproduce the recorded
   `foreground_pixels` and `horizontal_ink_profile` exactly, and every rebuilt Otsu threshold equals the recorded one.
   Zero `mask_mismatch` exclusions. A nonzero count means Task 1 is wrong and the slice stops.
3. **Synthetic estimator accuracy.** On at least 24 committed block fixtures spanning x-height 8 to 40 px, stroke 1 to 5
   px, skew 0, plus and minus 0.5 and 1.0 degrees, and gaps 2 to 20 px, the estimator recovers baseline row within 1 px,
   x-height within 1 px, stroke width within 1 px, and the word-run count exactly, on 100 percent of fixtures.
4. **Reviewed line correctness.** Provisional until open decision 7 settles who judges. At least 200 matched lines
   across at least three admitted books, rendered with baseline and x-height drawn: at least 0.95 judged correct, where
   correct means the baseline lies within 2 px of the visible baseline and the x-height line within 2 px of the
   lowercase top. The threshold and the 2 px tolerance stand regardless of reviewer; what is undecided is whether a
   model or a person applies them, which the M15b precedent recorded explicitly rather than left implicit. Pin that
   before running the gate, and record the choice with the result.
5. **Book-level stability.** For each admitted book, the MAD of per-page x-height medians is at most 0.08 times the
   book's pooled x-height. Pre-registered and uncalibrated.
6. **Word reconciliation floor.** At least 0.50 of measured lines per admitted book reconcile their ink-run count with
   their transcription word count. A sanity floor that catches a broken gap detector, not a claim that PGDP text agrees
   with the ink. A book below it is reported, not failed.
7. **Latent discipline.** The denylist and estimate-shape test passes on the real corpus report, not only on fixtures.
8. **Sample-size answer.** The Task 8 calibration number is measured and recorded for every admitted book.

Gates 5 and 6 carry pre-registered but uncalibrated numbers. Per the M15b rule, if either fails, record the exact
counts, leave this plan `partial`, and open a follow-up. Do not weaken a gate inside the same review run.

## The 30-page admission minimum

The intent map says the 30-page seed cannot be calibrated until something downstream states how many pages a per-book
typography fit needs, and names this plan as that consumer. The honest split:

**This slice can answer it for font-free observables, and Task 8 does.** Every observable here is a scalar pooled by a
two-stage median, so its stability against page count is directly measurable from data this slice already produces.
Stated before running so the measurement can contradict it: with per-page medians scattering by roughly 1 px and body
pages carrying about 30 matched lines each, a book-level x-height should settle within 0.5 px somewhere around 10 to 15
pages, making 30 comfortably sufficient.

**This slice cannot answer it for font fitting.** That requirement depends on how the candidate space is parameterised,
how many glyph instances per setting the scoring needs, and how many page classes must be fit separately. None of those
exist, so any number offered now would be invented.

Recommendation: record the measured font-free number, leave `MINIMUM_ACCEPTED_PAGES_PER_BOOK` at 30, and state in
`decisions.md` that the constant now has one calibrated lower bound and one still-open consumer.

## Fonts, and machines with no fonts fetched

This slice uses none. It imports nothing from `fonts.py`, opens no font file, renders no text, and never invokes `make
fetch-fonts`. All eight gates are measurable on a bare checkout with no fonts present, because the estimator fixtures
are synthetic block bitmaps rather than rendered type.

That is correct sequencing, not only convenience. Fonts land in `recipes/gaelic/fonts/`, which is gitignored, and the
fetch script downloads six Gaelic families. The PGDP books this pipeline measures are English-language nineteenth and
early-twentieth-century Latin-type volumes. The candidate set this repo can fetch today is the wrong script for the
corpus it has measured, so building inverse rendering first would rank candidates that could not be right.

What this slice sets up but does not build, recorded so the later slice inherits it: a user-provided candidate-font
manifest with per-font licence notes and no committed font bytes; a pytest marker so font-dependent tests skip cleanly
where none are fetched; and a CLI that fails with an explicit "no candidate fonts configured" message rather than
silently ranking an empty set.

## Decisions taken

All eight settled by CT on 2026-09-03. The plan is approved for execution.

1. **Milestone name: M15d.** M15c stays reserved for rectification, which this slice is not.
2. **Measure in the source frame now.** A genuine departure from the design's stated order, taken
   deliberately. Segment-wise projection cuts skew smear by the width ratio, from 13.1 px across a
   1500 px line to 1.75 px across a 200 px segment at half a degree. The measured skew distribution
   becomes the evidence that scopes rectification, which is otherwise a slice with no typographic
   target to gate itself against.
3. **Mask-reading slice.** The report-only variant was rejected: it cannot produce x-height,
   ascender or descender extents, or stroke width, and x-height is the observable this milestone is
   about.
4. **Task 1 may refactor `alignment_image.py`.** One definition of ink beats duplicating the mask
   builder and trusting Gate 2 to catch the drift later.
5. **CLI name: `typography-pgdp`,** matching the `rank-pgdp` / `profile-pgdp` / `align-pgdp` family.
6. **Gates 5 and 6 record and follow up.** A failure records the exact counts, leaves this plan
   `partial`, and opens a follow-up. It does not block the slice, and it does not get weakened
   inside the same review run. Both numbers are reasoned seeds, so a failure may say more about the
   seed than about the code.
7. **Gate 4 is judged by a model reading rendered crops,** recorded explicitly as model-reviewed
   rather than signed off row by row. Same method as both prior M15b precision measurements, and
   repeatable whenever the estimator changes.
8. **Twelve evidence pages per book.**

## Final review and handoff

Request a branch-wide review against the design and this plan. Resolve every accepted finding with a focused test. Rerun
`make ci AI=1`, the deterministic corpus replay, the review ledger, `docgraph check --strict`, and `git diff --check`
before claiming completion.

The handoff must state that font candidates, inverse rendering, typeface ranking, rectification, rectified frames,
change-point detection, and any point-size or leading claim remain unimplemented.
