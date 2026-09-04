---
Status: active
Owner: CT
Created: 2026-09-03
Last verified: 2026-09-04
Kind: research
---

# PGDP F2 Silently Rejoins Line-Break Hyphens

## Agent Index

- **Kind:** research
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-03
- **Last verified:** 2026-09-04
- **Provenance:** measured on 2026-09-03 over 41,708 F2 lines in the five whole-book PGDP projects
  under `/workspaces/pdomain-data/pgdp-corpus`, against the M15d word-reconciliation results
- **Disposition:** Active finding. Its predicted consequence was retracted on 2026-09-03 and
  reinstated on 2026-09-04, when the mechanism was confirmed directly and measured at 10 to 31
  percent of the surviving disagreement. See "The mechanism was confirmed on 2026-09-04."
- **Read when:** interpreting word-run reconciliation, changing the word-gap threshold, or deciding
  whether the pipeline needs OCR.
- **Search terms:** PGDP, F2, hyphen, line break, dehyphenation, word reconciliation, over-split,
  Gate 6, OCR witness.

## Goal

Establish whether PGDP F2 records a word broken across two printed lines, and what its answer does
to M15d's word-run reconciliation.

It does not record them. Across all five books, 41,708 non-blank F2 lines, exactly zero end in a
word-break hyphen. Every in-page break has been rejoined by proofers, with the whole word written
onto the line where it started. The ink still shows the break; the transcription no longer does.

This is not a parser gap. `alignment_source.py:381` builds `visible_text` by concatenating
markup-stripped fragments, and nothing in that file has any concept of a join, a continuation, or a
hyphen. There is nothing to fix there, because the information is not in the input.

## Method

Read `rounds/F2.json` for each of the five whole-book projects and classified every non-blank line
by how it ends and how it begins. A word-break hyphen is a letter followed by a single trailing `-`;
a line ending `--` or longer is an em dash, not a break. Page-boundary pairing was tested by walking
pages in natural page order and asking whether a line beginning `*` follows a page whose last line
ends `-*`.

Line lengths on one body page were tabulated separately to distinguish a rejoin from a dropped line.

## Evidence

| book | F2 lines | ends `-*` | starts `*` | ends in a word hyphen | ends in a dash |
| --- | ---: | ---: | ---: | ---: | ---: |
| projectID609bfa0449bdf | 6,843 | 13 | 14 | 0 | 10 |
| projectID64a479f51ce5b | 10,164 | 13 | 24 | 0 | 98 |
| projectID603d7d5e04ca0 | 11,157 | 6 | 7 | 0 | 226 |
| projectID657550412c8dc | 11,503 | 27 | 32 | 0 | 7 |
| projectID67a80fde44d34 | 2,041 | 3 | 3 | 0 | 2 |
| **total** | **41,708** | **62** | **80** | **0** | **343** |

The 343 lines in the last column all end in `--` or longer, as in `blotted out by this time:--`.

Line lengths confirm a rejoin rather than a dropped line. On `projectID609bfa0449bdf/p010.png` the 23
F2 lines run 19 to 55 characters with a median of 47, so F2 keeps one line per printed line. Words
are joined inside those lines, not moved between them.

**The page-boundary marker works where it is applied.** Of 57 `-*` line endings that have a following
page, 54 pair with a `*` opening the next page and 3 do not. The 80 `*` openings do not all pair
back, and the unpaired ones are mostly not hyphens: `*[Illustration: Fig. 4.--Breaking-down Mill.]`
and `*--ay, hard and bitter as that weedy swamp` continue a block and an em dash. So `*` marks a
continuation of any kind.

The conclusion is narrower and worse than "the marker is unreliable". The marker is applied at page
boundaries and nowhere else, and in-page breaks outnumber page-boundary breaks by roughly the number
of lines on a page.

## Conclusions

**Every silent join costs exactly one over-split, always on the following line, and never an
under-split.** Take `furniture` printed as `furni-` then `ture`. F2 writes `furniture` at the end of
the first line, which still balances at one ink run to one word. The next line does not: its leading
ink run, `ture`, has no F2 word to bind to, so the reconciler sees one run more than the
transcription has words.

**The predicted consequence was tested on 2026-09-03 and did not hold.** Two predictions follow
from the mechanism: the first matched line of a page is protected by the `*` marker and should
over-split less than later lines, and the orphan leading run should be a narrow word fragment.
Neither survived. In `projectID609bfa0449bdf` first lines reconcile *worse* than later lines,
0.580 against 0.636. The median leading-run width, as a share of the first F2 word's expected
share, is 0.957 on over-split lines against 1.017 on exact ones in that book, and 0.990 against
1.011 in `projectID657550412c8dc`. A fragment would be far narrower than that.

**A second cause was much larger at the time.** The shipped gap threshold was too low in every
book and split inside words at ordinary letter gaps. See
[the word-gap threshold finding](2026-09-03-word-gap-threshold-is-too-low.md), which shipped on
2026-09-04 and lifted the worst book from 0.208 to 0.800. An earlier version of this document
claimed the threshold was not the problem and argued against raising it. That was wrong, and
backwards: a threshold that is too low is exactly what produces a high over-split rate.

## The mechanism was confirmed on 2026-09-04

**Both of this document's retractions were themselves too strong.** With the threshold fixed, the
rejoining mechanism was confirmed directly and is the largest single named cause of what remains.

Twenty-four of the over-split lines in `projectID657550412c8dc` that no threshold can fix were
cropped and read. Every one is ordinary justified body text beginning with a word fragment carried
over from the line above. One example carries the whole mechanism: the ink reads `ness which may
justly be extended to con-`, eight runs, while F2 reads `which may justly be extended to
confirmed`, seven words. F2 moved `ness` onto the previous line and completed `con-` on this one.

A repair test then measured it in all five books. For each line over-split by exactly one, dropping
the *leading* run fits the F2 word widths best in 0.168 to 0.736 of cases, against about 0.02 for
any other single drop position. Fragment lines are 3.3 to 6.8 percent of all matched lines and
account for 10 to 31 percent of each book's remaining disagreement.

That 3.3-to-6.8 percent range is an independent measurement of the 4.5 percent line-end
hyphenation rate this document could only infer. The inference was right.

**The 2026-09-03 retraction was wrong because it compared against the wrong denominator.** It
bounded the mechanism at 4 to 5 of 24 percentage points of over-split. The 24 points were
dominated by a broken threshold. Fixing the threshold left a much smaller residual, and the same
absolute effect is now a much larger share of it.

**The page-boundary control was underpowered, not negative.** Only about 4.5 percent of page ends
carry a break, so the expected difference between first lines of a page and later lines is roughly
5 points, while each book has 32 to 212 first lines and a standard error of 3 to 7 points.
`projectID657550412c8dc` measured -5.2 points against its 6.0 percent fragment rate, which matches
the mechanism and still reads as z = -1.59. The control could never have resolved the effect.

The leading-run width test was a different mistake. It compared the leading ink run against the
first F2 word, but under rejoining those are different words: the ink's first run is the fragment
and F2's first word is the one after it. The test asked the wrong question.

See [what word reconciliation still
misses](2026-09-04-what-word-reconciliation-still-misses.md) for the full measurement.

## What this does NOT establish

**It did not explain the 2026-09-03 Gate 6 failure, and it still does not.** That failure was
[a gap threshold too low in every book](2026-09-03-word-gap-threshold-is-too-low.md). This
mechanism is the largest named cause of what survives the fix, which is a different and much
smaller quantity.

**The 4.5 percent rate was inferred and is now measured, at 3.3 to 6.8 percent per book.** The
inference assumed page-final lines hyphenate at the same rate as all other lines, and the repair
test on 2026-09-04 confirms that assumption held. F2 has still erased the direct evidence, so the
rate cannot be read off F2 itself.

**It says nothing about whether the 62 marked page-boundary breaks are handled correctly today.**
They were counted, not traced through the reconciler.

**It does not show that OCR would fix the gap.** It shows only that OCR is the sole available witness
to what ink is on the line.

## Next steps

1. Done on 2026-09-03, and it refuted the mechanism. Both the page-boundary control and the
   leading-run width test came back negative, and the cause was
   [the gap threshold](2026-09-03-word-gap-threshold-is-too-low.md).
2. Done on 2026-09-04, and the page-boundary control still shows no consistent effect.
   Restricted to body pages, first lines of a page disagree less than later lines in
   `projectID609bfa0449bdf`, `projectID603d7d5e04ca0`, and `projectID657550412c8dc` and more in
   the other two. Only `projectID603d7d5e04ca0` is significant, at z = -4.17 in the predicted
   direction; the rest fall between -1.59 and +0.66. That is one book of five, which neither
   supports the mechanism across the corpus nor refutes it there. The leading-run width test was
   not repeated. See [what word reconciliation still
   misses](2026-09-04-what-word-reconciliation-still-misses.md).
3. Scoped on 2026-09-04 as [the OCR witness
   plan](../plans/2026-09-04-pgdp-ocr-witness-for-continuation-fragments.md). F2 stays the label
   and ink projection stays the geometry; OCR supplies only correspondence, telling us a line's
   leading run is a continuation fragment. The pass needs no OCR engine in this repo, because the
   project's own fine-tuned doctr records already cover all five corpus books and pin to the same
   page hashes this repo pins to.

## Related

- [The word-gap threshold is too low in every book](2026-09-03-word-gap-threshold-is-too-low.md)
  — the finding that replaced this one as the explanation of over-split.
- [What word reconciliation still misses](2026-09-04-what-word-reconciliation-still-misses.md)
  — where this mechanism was confirmed directly and measured across all five books.
- [PGDP OCR witness for continuation fragments](../plans/2026-09-04-pgdp-ocr-witness-for-continuation-fragments.md)
  — the witness pass this finding asked for, scoped and measured for feasibility.
- [M15d font-free typographic observables](../plans/2026-09-02-pgdp-font-free-typographic-observables.md)
  — Gate 6 and the gap-threshold sweep.
- [PGDP typography and structure synthesis design](../specs/2026-08-22-pgdp-typography-structure-synthesis-design.md)
  — the slice an OCR witness pass would sit in front of.
