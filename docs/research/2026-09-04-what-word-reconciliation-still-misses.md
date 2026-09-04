---
Status: active
Owner: CT
Created: 2026-09-04
Last verified: 2026-09-04
Kind: research
---

# What Word Reconciliation Still Misses

## Agent Index

- **Kind:** research
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-04
- **Last verified:** 2026-09-04
- **Provenance:** measured on 2026-09-04 over 17,205 matched lines in the five whole-book
  `alignment-t2-*` reports at each book's shipped `ink-profile-word-runs/v2` threshold, with the
  replay validated line for line against a full-evidence pipeline run of
  `projectID67a80fde44d34`
- **Disposition:** Active finding. Explains the disagreement that survives the v2 threshold fix
  and argues Gate 6's line-level metric overstates it by roughly five times.
- **Read when:** reading Gate 6, choosing a metric for word-box quality, or deciding whether word
  segmentation needs a witness beyond gap width.
- **Search terms:** word reconciliation, over-split, per-gap error, Gate 6, letterspacing,
  residual, threshold jitter.

## Goal

Find out what the word-run disagreement that survives `ink-profile-word-runs/v2` actually is.

**The detector is far more accurate than Gate 6 reports.** It gets 91.5 to 97 percent of
individual word gaps right, while Gate 6 says 59 to 81 percent of lines are correct. A line
carries six to twelve gaps, so one bad gap fails the whole line. Most of what is left is a letter
gap sitting one pixel over the threshold, which no single book-wide threshold can remove.

## Method

Word-run detection was replayed over every matched line in the five alignment reports at that
book's shipped threshold: 10, 6, 8, 15, and 9 px. Each disagreeing line was then swept from 2 to
60 px to ask whether *any* threshold would reconcile it.

The replay was validated first. `projectID67a80fde44d34` was re-run with `--evidence-pages 40`,
which emits per-line rows for all 32 of its pages, and the replay agreed with the pipeline on all
763 shared lines with zero differences. The replay also sees 66 lines the pipeline excludes for
geometry, which moves the book's rate by 0.0005. It is a valid stand-in.

## Evidence

### The per-gap error rate is a fifth of the line error rate

| book | lines disagreeing | true word gaps | run errors | per-gap error |
| --- | ---: | ---: | ---: | ---: |
| projectID609bfa0449bdf | 0.189 | 35,592 | 1,153 | 0.032 |
| projectID64a479f51ce5b | 0.259 | 37,766 | 1,126 | 0.030 |
| projectID603d7d5e04ca0 | 0.380 | 28,378 | 2,410 | 0.085 |
| projectID657550412c8dc | 0.197 | 22,214 | 1,276 | 0.057 |
| projectID67a80fde44d34 | 0.217 | 5,481 | 226 | 0.041 |

### Almost every disagreement is reachable by some threshold

| book | disagrees | reconcilable at some threshold | at no threshold | of those, text exceeds ink |
| --- | ---: | ---: | ---: | ---: |
| projectID609bfa0449bdf | 0.189 | 0.157 | 0.033 | 0 of 165 |
| projectID64a479f51ce5b | 0.259 | 0.186 | 0.072 | 2 of 220 |
| projectID603d7d5e04ca0 | 0.380 | 0.293 | 0.087 | 5 of 397 |
| projectID657550412c8dc | 0.197 | 0.159 | 0.038 | 5 of 142 |
| projectID67a80fde44d34 | 0.217 | 0.177 | 0.040 | 0 of 33 |

### Over-split has two regimes, and they split the corpus

For each over-split line, take the gaps at or above the book threshold and find the narrowest.
How far above the threshold it sits says what the extra split was.

| book | narrowest is 0-1 px above | 4+ px above | same on lines that reconcile (0-1 px) | narrowest / widest |
| --- | ---: | ---: | ---: | ---: |
| projectID609bfa0449bdf | 0.655 | 0.169 | 0.108 | 0.50 |
| projectID64a479f51ce5b | 0.749 | 0.044 | 0.304 | 0.46 |
| projectID67a80fde44d34 | 0.519 | 0.260 | 0.121 | 0.52 |
| projectID603d7d5e04ca0 | 0.211 | 0.349 | 0.093 | 0.63 |
| projectID657550412c8dc | 0.252 | 0.536 | 0.111 | 0.71 |

## Conclusions

**Gate 6 measures lines, and the thing a labeler consumes is gaps.** At 0.593, the worst book has
an 8.5 percent per-gap error. At 0.805, the best has 3.2 percent. Line-level agreement is a valid
gate for catching a broken detector, which is what it was written for, but it is the wrong number
to quote as the quality of the word boxes.

**PGDP text is not adding words.** Across all five books, 12 lines in total have more
transcription words than the ink has separable runs at the finest threshold. Every other
unreconcilable line has enough ink; the run count simply jumps over the target as the threshold
rises, because several gaps of the same width collapse at once.

**In three books the over-split is threshold jitter, and it is irreducible.** In
`projectID609bfa0449bdf`, `projectID64a479f51ce5b`, and `projectID67a80fde44d34`, the extra split
comes from a gap sitting 0 or 1 px above the threshold in 52 to 75 percent of over-split lines,
against 11 to 30 percent on lines that reconcile, and that gap is about half the width of the
line's widest. It is a letter gap that crept over the line. Moving the threshold a pixel trades
those over-splits for under-splits, which is exactly the plateau the original sweep found: the
best swept threshold for these books is within 1 px of the Otsu value and buys 2 to 4 points.

**In two books the over-split is genuinely wide gaps, and it is not a threshold problem at all.**
In `projectID603d7d5e04ca0` and `projectID657550412c8dc`, the narrowest accepted gap sits 4 or
more px above the threshold in 35 and 54 percent of over-split lines, and its median ratio to the
line's widest gap is 0.63 and 0.71. Those lines carry several gaps of comparable width, so no
threshold separates their letters from their words. `projectID603d7d5e04ca0` is the worst book on
Gate 6 because it has both regimes: 1,306 over-split lines and a third of them structurally
unfixable.

**Em dashes are a real but small contributor.** Lines containing `--` disagree more than others in
every one of the five books: 0.230 against 0.187, 0.414 against 0.251, 0.550 against 0.370, 0.327
against 0.195, and 0.300 against 0.215. Multiplying the excess by the number of such lines, they
explain 1 to 3 percent of each book's disagreement. Consistent direction, small share.

**Short lines have a much higher per-gap error and still are not where the errors are.** Lines of
one to five words run 0.106 to 0.162 per gap, three to five times the long-line rate, in every
book. But they carry few gaps each, so they contribute 3.6 to 16.9 percent of run errors. Most of
the absolute error sits on ordinary body lines.

## What this rules out

**Display type is not the cause, as stated.** All-capital lines reconcile *better* than mixed-case
ones, not worse: 0.048 against 0.406 in `projectID603d7d5e04ca0` and 0.067 against 0.190 in
`projectID609bfa0449bdf`. Two books show the reverse on samples of 11 and 27 lines, which is
noise. Whatever the wide-gap regime is, an all-capital setting is not a usable proxy for it.

**Line boxes spanning unrelated ink are negligible.** A box carrying an interior gap of 100 px or
more occurs 0 to 32 times per book, under 0.7 percent of lines, and accounts for under 1 percent
of run errors in every book.

**The line-break hyphen mechanism still shows no consistent effect.** Restricted to body pages,
first lines of a page, which the `*` marker protects, disagree less than later lines in three
books and more in two. Only `projectID603d7d5e04ca0` is significant, at z = -4.17 in the predicted
direction; the other four are between -1.59 and +0.66. This is the re-test that
[the hyphen finding](2026-09-03-pgdp-f2-line-break-hyphens.md) asked for once over-splitting was
reduced. It does not support the mechanism, and it does not refute it in that one book.

## What this does NOT establish

**The wide-gap regime is not identified.** It is measured, not explained. The lines are known to
carry several gaps of comparable width; what typographic setting produces that was not
established, and the two obvious guesses, all-capital lines and boxes spanning stray ink, were
both tested and failed.

**The per-gap error rate counts net run errors, not misplaced boundaries.** `abs(runs - words)`
summed over lines divided by total word gaps is a lower bound on boundary errors: a line that
over-splits once and under-splits once elsewhere scores zero. The true per-gap error is somewhat
higher than the 3.0 to 8.5 percent quoted.

**Nothing here was validated against a human reading of a word box.** F2 word counts remain the
only reference, and they are fallible. Every rate above measures agreement with that reference.

**The threshold sweep bounds at 60 px.** A line needing a wider threshold is counted as
unreconcilable. Given book thresholds of 6 to 15 px, this bound is unlikely to bind, but it was
not tested.

## Next steps

1. Put to CT whether the reported quality of word boxes should be per-gap rather than per-line.
   Gate 6 itself should stay as it is; it did its job.
2. Identify the wide-gap regime by looking at the actual pages of
   `projectID657550412c8dc` where over-split lines cluster, rather than by proxy from the text.
3. Leave threshold jitter alone. Three books are at the noise floor of any single global
   threshold, and moving it trades one error for another.

## Related

- [The word-gap threshold is too low in every book](2026-09-03-word-gap-threshold-is-too-low.md)
  — the finding whose fix produced the residual measured here.
- [F2 silently rejoins line-break hyphens](2026-09-03-pgdp-f2-line-break-hyphens.md) — re-tested
  above and still unsupported.
- [M15d font-free typographic observables](../plans/2026-09-02-pgdp-font-free-typographic-observables.md)
  — Gate 6 and its 0.50 floor.
