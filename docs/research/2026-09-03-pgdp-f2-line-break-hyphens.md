---
Status: active
Owner: CT
Created: 2026-09-03
Last verified: 2026-09-03
Kind: research
---

# PGDP F2 Silently Rejoins Line-Break Hyphens

## Agent Index

- **Kind:** research
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-03
- **Last verified:** 2026-09-03
- **Provenance:** measured on 2026-09-03 over 41,708 F2 lines in the five whole-book PGDP projects
  under `/workspaces/pdomain-data/pgdp-corpus`, against the M15d word-reconciliation results
- **Disposition:** Active finding. Constrains how M15d Gate 6 should be read and scopes an OCR
  witness pass.
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

That is the right shape for what M15d measured. Sweeping the gap threshold gave 0.242 over-split
against 0.040 under-split at 6 px, and a one-per-break bias in a single direction is what produces
that asymmetry.

**The word-gap threshold is not what is wrong.** The plan measured the threshold curve as flat
between 5 and 8 px, and the book failing hardest at 0.208 reconciliation has the corpus's widest
measured word gap, 25 px against a 4 to 5 px threshold, so the detector is not under-splitting.
Widening it would trade a real measurement for a passing number.

**Gate 6 is partly a measurement of F2's line-joining policy.** A gate demanding exact run-to-word
agreement charges the detector for a transcription convention it cannot see.

## What this does NOT establish

**It does not explain Gate 6 on its own.** 62 page-final lines across about 1,385 pages puts
line-end hyphenation near 4.5 percent of line ends. Applied to 41,708 lines that is on the order of
1,900 silent in-page joins, so roughly 4 to 5 of the 24 percentage points of over-split. The worst
book reconciles at 0.208 and needs 0.29 more to clear the 0.50 floor. Something else is also wrong
there, and it has not been identified.

**The 4.5 percent rate is inferred, not measured.** It assumes page-final lines hyphenate at the
same rate as all other lines. F2 has erased the direct evidence, so the rate cannot be measured from
F2 at all.

**It says nothing about whether the 62 marked page-boundary breaks are handled correctly today.**
They were counted, not traced through the reconciler.

**It does not show that OCR would fix the gap.** It shows only that OCR is the sole available witness
to what ink is on the line.

## Next steps

1. Trace the 62 marked `-*` page-boundary breaks through reconciliation. They are the one place where
   a split is known to have happened, so they give a ground-truth sample for confirming the
   one-per-break over-split mechanism before building anything.
2. Measure over-split against under-split per book for the two failing books, which is the M15d
   Gate 6 follow-up this finding partly answers.
3. Scope an OCR witness pass. F2 stays the label and ink projection stays the geometry; OCR supplies
   only correspondence, telling us a line's leading run is a continuation fragment. A
   `continuation_fragment` flag with a stated one-token tolerance is then a rule with a reason rather
   than a tolerance widened until things pass.

## Related

- [M15d font-free typographic observables](../plans/2026-09-02-pgdp-font-free-typographic-observables.md)
  — Gate 6 and the gap-threshold sweep this finding constrains.
- [PGDP typography and structure synthesis design](../specs/2026-08-22-pgdp-typography-structure-synthesis-design.md)
  — the slice an OCR witness pass would sit in front of.
