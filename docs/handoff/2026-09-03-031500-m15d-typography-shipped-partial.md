---
kind: handoff
status: "active"
created: "2026-09-03"
created_at: "2026-09-03T03:15:00Z"
owner: CT
branch: master
scope: pgdp-synthesis
worktree: /workspaces/pdomain/pdomain-ocr-synth
base_commit: "cfc0444ea9ea17f5142df717f4bc89eb1746e877"
supersedes: "2026-09-02-210255-m15b-residuals-fixed-and-contracts-decision.md"
handoff_reason: milestone_partial
host: claude-code
---

# M15d ships font-free typography; one gate fails in two books

## Goal

Add a local `typography-pgdp` command that measures typographic observables from
aligned ink and pools them per book and per page class, using no font candidates
at all. All eight tasks of
[the plan](../plans/2026-09-02-pgdp-font-free-typographic-observables.md)
landed. The plan is `partial` because Gate 6 fails in two of five books.

## What landed

Eight commits, one per task, each gated on `make ci AI=1`.

| commit | task |
| --- | --- |
| `c38ce59` | 1. `alignment_image.build_candidate_mask` plus the round-trip test |
| `c03f121` | 2. per-line baseline, x-height, extents, stroke, skew |
| `782c843` | 3. word runs, reconciliation, baseline pitch |
| `441b939` | 4. the `pgdp-typography/v1` wire contract and its schema |
| `690d069` | 5. two-stage pooling per book and page class |
| `c62a93f` | 6. orchestration and the `typography-pgdp` command |
| `1762944` | 7. reviewed fixtures and the baseline review overlay |
| `273e8b2` | a pooling-scope fix the corpus forced |
| `cfc0444` | 8. the corpus run and every measured gate |

The command reads a `pgdp-alignment/v3` report with the `pgdp-profile/v2`
profile it recorded, refuses to run unless the profile hashes to the recorded
value, rebuilds each accepted page's ink mask, measures every matched line, and
writes a deterministic `pgdp-typography/v1` report. It opens no font, renders no
text, and never leaves the `source` frame.

## Every gate, measured

Evidence is in `/workspaces/pdomain/.m15d-evidence/` (`gates.json`, the ten
per-book reports, and 21 Gate 4 review sheets).

| Gate | Result | Verdict |
| --- | --- | ---: |
| 1. Determinism | 5 of 5 books byte-identical across two runs | pass |
| 2. Mask reproduction | 665 measured pages, 17,205 matched candidates verified, 0 `mask_mismatch` | pass |
| 3. Synthetic estimator | 34 of 34 fixtures within 1 px, plus 8 reviewed fixtures | pass |
| 4. Reviewed line correctness | 208 of 210 judged correct, 0 incorrect, 0.9905 | pass |
| 5. Book-level stability | relative MAD 0.000 in all 5 books against a 0.08 ceiling | pass |
| 6. Word reconciliation | 0.620, 0.539, 0.520 pass; 0.476 and 0.208 fail | 3 of 5 |
| 7. Latent discipline | 0 violations across all 5 corpus reports | pass |
| 8. Sample-size answer | measured for every book | pass |

Gate 2 is the one that had to be exact. Every one of 17,205 matched candidates
reproduced its recorded `foreground_pixels` and `horizontal_ink_profile` from
the rebuilt mask, and every rebuilt Otsu threshold equalled the recorded one.

Gate 4 was model-reviewed, as decision 7 settled, using
`render_line_typography_overlay` at 3x on a 460 px window, ten crops to a sheet.
The two lines not counted correct are all-capital and small-capital lines that
carry no lowercase, so the "within 2 px of the lowercase top" half of the
criterion has nothing to measure against. Both of their baselines were correct.
Counting them as failures still clears 0.95.

Gate 5's MAD of exactly 0 in every book is real rather than degenerate. Per-page
medians are integers and a page of body text at one size gives the same integer
page after page; the 16th and 84th percentiles in `extensions` sit within 1 px
of the median.

## What is left partial

**Gate 6 fails in two books and was not weakened.**

| book | reconciled / measured | rate |
| --- | ---: | ---: |
| projectID609bfa0449bdf | 2801 / 4515 | 0.620 |
| projectID64a479f51ce5b | 1547 / 2868 | 0.539 |
| projectID67a80fde44d34 | 397 / 763 | 0.520 |
| projectID603d7d5e04ca0 | 1692 / 3553 | 0.476 |
| projectID657550412c8dc | 739 / 3546 | 0.208 |

The follow-up is specific: measure over-split against under-split counts per
book for the two failing books before touching the gap threshold. The book at
0.208 has the corpus's widest measured word gap, 25 px against a 4 to 5 px
threshold derived from its 18 px x-height, so over-splitting on inter-letter
spacing is the likelier cause than under-splitting. Guessing at the threshold
without that measurement would be tuning against one book.

## The sample-size answer, and what it does not settle

Body pages were shuffled with a fixed seed, pooled at n = 5, 10, 20, 30, 50,
100, truncated at each book's own body-page count, and compared against the
full-book value at 0.5 px.

| book | body pages | x-height | pitch | stroke | word gap |
| --- | ---: | ---: | ---: | ---: | ---: |
| projectID609bfa0449bdf | 212 | 20 | 5 | 5 | did not converge |
| projectID64a479f51ce5b | 71 | 5 | 5 | 5 | 5 |
| projectID603d7d5e04ca0 | 168 | 5 | 5 | 5 | 5 |
| projectID657550412c8dc | 149 | 5 | 5 | 5 | 50 |
| projectID67a80fde44d34 | 32 | 5 | 5 | 5 | 20 |

Five body pages are enough for x-height, baseline pitch, and stroke width in
four books and twenty in the fifth, so 30 is comfortably sufficient for those
three. Word gap is the unstable observable: one book needs 50 pages and one has
not settled at 100. `MINIMUM_ACCEPTED_PAGES_PER_BOOK` stays at 30 and now has
one calibrated lower bound and two still-open consumers, word gap and font
fitting.

## Two corrections a later reader needs

**Use the `alignment-t2-*` reports, not `alignment-wholebook-*`.** Both sets sit
in `/workspaces/pdomain/.m15b-evidence/`. Only the t2 set carries the
page-classification fixes. The wholebook set accepts 367 pages, classes one
whole book `unknown`, and accepts nothing at all in
`projectID67a80fde44d34`; the t2 set accepts 665 and matches the per-book counts
the plan quotes. The plan's two earlier 2026-09-03 measurements were taken from
the wholebook set, and their conclusions still hold because they measure line
widths and gap thresholds rather than page counts.

**Book estimates pool every measured page, styles do not.** Originally both were
class-gated. Measured against the wholebook reports, one book classed all 52 of
its accepted pages `unknown` and so reported no estimates at all while carrying
902 measured lines. A book-level median is a statement about the book, not about
one template, so `273e8b2` changed it. Unknown pages are still excluded from
every style as `"{page_name}:unpooled_page_class"`.

## Still not implemented

Font candidates, inverse rendering, typeface ranking, rectification, rectified
frames, change-point detection over page index, and any point-size or leading
claim. None of it is started. The measured skew distribution is now recorded per
page, style, and book, which is the evidence a rectification slice would need to
scope itself.

This repo still has unpushed commits on `master`. Nothing here was pushed.

## Resume steps

1. Measure over-split against under-split word counts per book for
   `projectID603d7d5e04ca0` and `projectID657550412c8dc`, then decide whether the
   gap threshold needs a per-book term. That closes Gate 6 and moves the plan
   from `partial` to complete.
2. Ask CT whether Gate 4's model-reviewed verdict is enough, or whether the 210
   sheets in `.m15d-evidence/gate4-sheets/` want a human pass.
3. Before any later slice reruns the corpus, use the `alignment-t2-*` reports.

## Pointers

- [the M15d plan](../plans/2026-09-02-pgdp-font-free-typographic-observables.md)
- [the typography design](../specs/2026-08-22-pgdp-typography-structure-synthesis-design.md)
- [previous handoff](2026-09-02-210255-m15b-residuals-fixed-and-contracts-decision.md)
- `/workspaces/pdomain/.m15d-evidence/gates.json` — every gate number
- `/workspaces/pdomain/.m15d-evidence/gate4-sheets/` — the 21 review sheets
