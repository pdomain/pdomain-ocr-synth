---
Status: active
Owner: CT
Created: 2026-09-03
Last verified: 2026-09-03
Kind: research
---

# The Word-Gap Threshold Is Too Low in Every Book

## Agent Index

- **Kind:** research
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-03
- **Last verified:** 2026-09-03
- **Provenance:** measured on 2026-09-03 over 17,205 matched lines in the five whole-book
  `alignment-t2-*` reports, sweeping the gap threshold from 2 to 20 px per book and comparing
  against an Otsu split of each page's own gap-length distribution
- **Disposition:** Active finding. Identifies the cause of M15d Gate 6 and proposes the fix.
  Not yet implemented.
- **Read when:** changing word segmentation, reading Gate 6, or judging whether the reconciliation
  ceiling is real.
- **Search terms:** word gap, threshold, over-split, Gate 6, Otsu, reconciliation, ink profile.

## Goal

Find why M15d's word reconciliation fails Gate 6 in two of five books.

The shipped gap threshold, `max(2, round(0.25 * x_height_px))`, is too low in every book. It
splits inside words at ordinary letter gaps, which is what the measured over-split has been
reporting all along. Raising it to a value derived from each page's own gap distribution lifts
reconciliation from 0.217 to 0.814 in the worst book and clears the 0.50 floor in all five.

**This reverses an earlier claim.** The
[hyphen finding](2026-09-03-pgdp-f2-line-break-hyphens.md) concluded that the threshold was not
the problem. That was wrong, and the reasoning was backwards: a threshold that is too low causes
over-splitting, so the high over-split rate was the primary evidence *for* raising it, not
against.

## Method

For each of the five books, re-ran word-run detection over every matched line's stored
`horizontal_ink_profile` at every integer threshold from 2 to 20 px, and recorded the share of
lines whose run count exactly equals the transcription's word count.

Then, independently, derived a threshold per page by building a histogram of every zero-ink gap
length on that page's matched lines and applying the shipped Otsu implementation from
`image_measurement` to split it. Intra-word letter gaps and inter-word gaps are two populations;
Otsu finds the valley. That choice never consults the reconciliation rate, so agreement with the
swept optimum is evidence rather than tuning.

## Evidence

| book | x-height | shipped `t` | shipped exact | Otsu `t` (median) | Otsu exact | best `t` | best exact |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| projectID609bfa0449bdf | 15 | 4 | 0.633 | 10 | 0.802 | 11 | 0.841 |
| projectID64a479f51ce5b | 11 | 3 | 0.594 | 6 | 0.751 | 5 | 0.770 |
| projectID603d7d5e04ca0 | 17 | 4 | 0.430 | 7 | 0.608 | 6 | 0.634 |
| projectID657550412c8dc | 18 | 5 | 0.217 | 14 | 0.814 | 11 | 0.838 |
| projectID67a80fde44d34 | 17 | 4 | 0.527 | 9 | 0.790 | 10 | 0.803 |

Three things follow from the table.

**The shipped threshold is below the optimum in all five books,** by 1 px in the best case and
by 6 px in the worst. There is no book where 0.25 of the x-height is right.

**x-height is a poor predictor of the optimum.** The ratio of the best threshold to x-height runs
0.35, 0.45, 0.59, 0.61, and 0.73. It is not 0.25 anywhere and it is not constant.

**Otsu on the page's own gaps recovers the optimum without being told it,** landing within 2 to 4
points of the swept best in every book, and within 1 px of the best threshold in two of them.

## Conclusions

**Gate 6 caught a real defect rather than a bad threshold choice.** At the Otsu threshold every
book clears the 0.50 floor: 0.802, 0.751, 0.608, 0.814, 0.790. The gate was correct and the
estimator was wrong.

**The 0.72 ceiling recorded in the M15d plan is an artifact.** That number came from sweeping one
absolute threshold across all books pooled, which averages over books whose optima differ from 5
to 11 px. Per page, the detector reaches 0.81.

**The fix is per-page, not per-book.** The Otsu threshold varies within a book, from 6 to 19 px in
`projectID657550412c8dc`, and a per-book constant would give up part of the gain. It also avoids
adding a hand-tuned per-book term, which would be tuning to the gate.

## What this does NOT establish

**It is not implemented.** Everything above is measured by re-running detection over stored ink
profiles. Changing `typography_measure` moves `WORD_SEGMENTATION_METHODS` to a v2 algorithm
version, invalidates the committed corpus numbers, and needs the reviewed fixtures regenerated.
That is a decision for CT, not a silent change.

**Exact run-to-word agreement is still not the right target.** Even at each book's optimum, 16 to
39 percent of lines disagree. PGDP text is fallible and so is gap detection, so some disagreement
is correct behaviour, and the remaining gap has not been attributed.

**Otsu is not proven optimal.** It was the first principled data-driven split tried and it worked.
A gap-histogram valley search or a per-line method was not compared against it.

**The comparison uses a fixed per-book x-height** for the shipped baseline rather than the real
per-line x-height the pipeline uses, so the shipped column is an approximation of shipped
behaviour, not a replay of it. The measured corpus rates it approximates are 0.620, 0.539, 0.476,
0.208, and 0.520.

## Next steps

1. Put the change to CT: move word segmentation to a `v2` algorithm version with a per-page
   Otsu-derived gap threshold, regenerate the reviewed fixtures, and re-run the corpus.
2. Re-measure Gate 6 afterwards and record whether the remaining disagreement is over-split,
   under-split, or genuine F2 error.
3. Keep the [hyphen finding](2026-09-03-pgdp-f2-line-break-hyphens.md) separate. It is a true fact
   about F2 with a much smaller effect than first claimed.

## Related

- [F2 silently rejoins line-break hyphens](2026-09-03-pgdp-f2-line-break-hyphens.md) — the theory
  this finding replaced as the main explanation of over-split.
- [M15d font-free typographic observables](../plans/2026-09-02-pgdp-font-free-typographic-observables.md)
  — Gate 6, and the 0.72 ceiling this finding corrects.
