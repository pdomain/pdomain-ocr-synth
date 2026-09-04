---
kind: handoff
status: "active"
created: "2026-09-04"
created_at: "2026-09-04T01:45:00Z"
owner: CT
branch: master
scope: pgdp-synthesis
worktree: /workspaces/pdomain/pdomain-ocr-synth
base_commit: "3b135a7df68aa9544674757444822dc86562f4a9"
supersedes: "2026-09-03-031500-m15d-typography-shipped-partial.md"
handoff_reason: milestone_complete
host: claude-code
---

# M15d is complete: the word-gap threshold now comes from each book's own gaps

## What changed

Word segmentation moved to `ink-profile-word-runs/v2`. Gate 6, the one gate M15d
failed, now passes in all five books, so
[the plan](../plans/2026-09-02-pgdp-font-free-typographic-observables.md) moves
from `partial` to `complete`.

The v1 rule, `max(2, round(0.25 * x_height_px))`, sat below the swept optimum in
every book, by 1 px in the best case and 6 px in the worst, so it split inside
words at ordinary letter gaps. v2 derives one threshold per book by Otsu over the
book's own pooled gap-length histogram. A pre-pass builds that histogram from the
`horizontal_ink_profile` values the alignment report already carries, so it opens
no image and costs one walk of a report being read anyway.

Two commits, both gated on `make ci AI=1`.

| commit | what |
| --- | --- |
| `3b135a7` | the v2 rule, its guard, the orchestration pre-pass, the tests, the regenerated fixtures |
| this one | the plan, both research docs, `current-state.md`, and this handoff |

## Every gate, re-measured

Evidence is in `/workspaces/pdomain/.m15d-evidence/`. `gates.json` now holds the
v2 numbers; the v1 numbers are preserved as `gates-v1-word-runs.json`.

| Gate | Result | Verdict |
| --- | --- | ---: |
| 1. Determinism | 5 of 5 books byte-identical across two runs | pass |
| 2. Mask reproduction | 665 measured pages, 17,205 matched candidates, 0 `mask_mismatch` | pass |
| 3. Synthetic estimator | 34 of 34 fixtures within 1 px, plus 8 reviewed fixtures | pass |
| 4. Reviewed line correctness | 208 of 210, 0.9905, carried over on byte-identical sheets | pass |
| 5. Book-level stability | relative MAD 0.000 in all 5 books against a 0.08 ceiling | pass |
| 6. Word reconciliation | 0.805, 0.742, 0.593, 0.800, 0.782 against a 0.50 floor | pass |
| 7. Latent discipline | 0 violations across all 5 corpus reports | pass |
| 8. Sample-size answer | measured for every book, and word gap now converges everywhere | pass |

Gate 6 in full, against the v1 rates it replaces:

| book | threshold | reconciled / measured | v2 | v1 |
| --- | ---: | ---: | ---: | ---: |
| projectID609bfa0449bdf | 10 px | 3636 / 4515 | 0.805 | 0.620 |
| projectID64a479f51ce5b | 6 px | 2129 / 2868 | 0.742 | 0.539 |
| projectID603d7d5e04ca0 | 8 px | 2107 / 3553 | 0.593 | 0.476 |
| projectID657550412c8dc | 15 px | 2838 / 3546 | 0.800 | 0.208 |
| projectID67a80fde44d34 | 9 px | 597 / 763 | 0.782 | 0.520 |

**Gates 1 through 5, 7 and 8 came back unchanged, which is the check that the
edit stayed inside word segmentation.** Gate 2 verifies the same 17,205
candidates across the same 665 pages with zero mismatches. Gate 5's relative MAD
is still exactly 0.000 and every pooled x-height is the same integer. Gate 8's
x-height, pitch, and stroke settle at exactly the same page counts as before.

**Gate 4 was not re-reviewed and did not need to be.** Re-rendering all 21 review
sheets from the v2 reports produced files byte-identical to the ones the 208-of-210
verdict was given on, and the index matched too. The overlay draws the line box,
the baseline, and the x-height rule; it draws no word boxes, so word segmentation
cannot move it.

**Gate 8's word gap improved.** It now settles at 5, 50, 5, 30, and 5 body pages.
Under v1 one book did not converge within 100.

## Three things the finding did not settle, settled here

**Book-level, not per-page.** The
[research finding](../research/2026-09-03-word-gap-threshold-is-too-low.md)
concluded the fix had to be per-page. Measured head to head over the same lines, a
per-book threshold scores 0.811, 0.741, 0.620, 0.803, 0.783 and a per-page one
scores 0.802, 0.751, 0.608, 0.814, 0.790. Book-level wins in three of five and no
difference exceeds 1.1 points, so the simpler rule ships and that conclusion is
marked overturned in the doc. Per-page values are recorded in each page's
`extensions` as evidence; their within-book ranges are 4 to 12, 4 to 7, 4 to 10,
6 to 19, and 8 to 10 px.

**Otsu's own separability cannot serve as the bimodality guard.** Otsu splits a
single hump down the middle if handed one, so the split has to be checked before
it is used. Separability looks like the natural check and is not: it scores 0.65
to 0.75 on a uniform, a single Gaussian, and a geometric decay against 0.83 to
0.85 on the real books. Valley depth, the count at the threshold over the smaller
class peak, separates them cleanly: 0.104 to 0.152 on the books against 1.00 to
1.18 on the same synthetic shapes. The shipped floor is 0.5. It fired on no book
and on 14 of 665 pages, all evidence-only, so nothing in the corpus took the
x-height fallback.

**Gaps wider than 64 px are clamped into one tail bin.** Line-end and paragraph
whitespace is not letter or word spacing, and left uncapped it drags the
inter-word class mean and pulls the split with it.

## What did not change

The wire contract. `pgdp-typography/v1` and
`schemas/pgdp-typography-v1.schema.json` are exactly as they were, and `make
schema` regenerates no diff. Only the method string inside `methods` moved to v2.
The chosen per-book threshold went into the report's `thresholds` and the per-page
Otsu splits into page `extensions`, both of which the contract already allowed.

The geometry estimator. `measure_line_typography` is untouched, which is why
Gates 1 through 5 and 7 reproduce.

The reviewed fixture bitmaps. All eight regenerated byte-identical; only the
manifest changed, to record the `gap_threshold_px` each case is measured at. That
value is the case's own book's measured threshold, so a fixture meets the rule the
corpus run applies to that book rather than a round number.

## Still open

**The residual disagreement is not attributed.** Over the evidence-sampled pages,
which are the ones carrying per-line rows, exact agreement runs 0.777, 0.790,
0.665, 0.726, 0.819, and what remains is mostly over-split in four books and
mostly under-split in `projectID657550412c8dc`. No cause is established. Exact
agreement with F2 was never the right long-run target: 0.80 means agreement with a
fallible reference, not correctness.

**The hyphen finding has not been re-tested under v2.** Its two direct tests, the
page-boundary control and the leading-run width comparison, were not repeated. With
over-splitting largely removed, a residual one-per-break bias would now be visible
if it exists. See [the hyphen
finding](../research/2026-09-03-pgdp-f2-line-break-hyphens.md).

**Gate 4 is still model-reviewed**, as decision 7 settled. Whether the 210 sheets
in `.m15d-evidence/gate4-sheets/` want a human pass is unanswered.

## Still not implemented

Font candidates, inverse rendering, typeface ranking, rectification, rectified
frames, change-point detection over page index, and any point-size or leading
claim. None of it is started.

This repo still has unpushed commits on `master`. Nothing here was pushed.

## Two corrections a later reader still needs

**Use the `alignment-t2-*` reports, not `alignment-wholebook-*`.** Both sit in
`/workspaces/pdomain/.m15b-evidence/`. Only the t2 set carries the
page-classification fixes; it accepts 665 pages against the wholebook set's 367.

**Background corpus runs get killed in this container.** Run each book in the
foreground, one shell call per book. The five books take about 2.5 minutes per
pass. `run_all.sh` in the evidence directory has the commands.

## Resume steps

1. Decide whether the residual disagreement is worth attributing, and if so start
   from `.m15d-evidence/residual.json`.
2. Re-run the hyphen finding's two tests under v2 if that attribution matters.
3. Decide whether Gate 4 wants a human pass.

## Pointers

- [the M15d plan](../plans/2026-09-02-pgdp-font-free-typographic-observables.md)
- [Word-gap threshold is too low](../research/2026-09-03-word-gap-threshold-is-too-low.md)
- [F2 line-break hyphens](../research/2026-09-03-pgdp-f2-line-break-hyphens.md)
- [the typography design](../specs/2026-08-22-pgdp-typography-structure-synthesis-design.md)
- [previous handoff](2026-09-03-031500-m15d-typography-shipped-partial.md)
- `/workspaces/pdomain/.m15d-evidence/gates.json` — every v2 gate number
- `/workspaces/pdomain/.m15d-evidence/gates-v1-word-runs.json` — the v1 numbers
- `/workspaces/pdomain/.m15d-evidence/book-otsu.json` — book and page thresholds
- `/workspaces/pdomain/.m15d-evidence/bimodality.json` — separability against valley depth
- `/workspaces/pdomain/.m15d-evidence/guard-count.json` — the 14 pages the guard flagged
- `/workspaces/pdomain/.m15d-evidence/residual.json` — over-split against under-split
