---
Status: active
Owner: CT
Created: 2026-09-07
Last verified: 2026-09-07
Kind: research
---

# Gate 3 Recheck on the 713-Page Alignment

## Agent Index

- **Kind:** research
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-07
- **Last verified:** 2026-09-07
- **Provenance:** measured on 2026-09-07 against the five whole-book inventories captured at
  commit `f9fdfef` in `/workspaces/pdomain/.extraction-baseline/`, compared glyph for glyph with
  the M15f inventories in `/workspaces/pdomain/.m15f-evidence/` and the 23 cells marked wrong in
  `gate3-review.json`; glyphs were matched by page and box, and the six unflagged survivors were
  read as rendered crops, not as text
- **Disposition:** Active finding. Rules out the standing hypothesis that re-running the chain on
  the current alignment would close Gate 3, records a comparison trap that inverted a first pass of
  this same analysis, and shows the gate's review sheet overstates the error rate because it hides
  `label_style`.
- **Read when:** deciding how to close Gate 3, changing the glyph review protocol, comparing two
  glyph inventories, or judging whether a measurement re-run is worth the time.
- **Search terms:** Gate 3, label correctness, small caps, label_style, quality flags,
  band identification, line_ordinal, glyph identity, italic word gap, glyph mislabel.

## Goal

Find out whether re-running the measurement chain on the current alignment closes Gate 3.

**It does not, and the margin is not close.** All 23 glyphs the M15f review marked wrong survive
the band-identification fixes unchanged. Not one is removed. Gate 3 fails on the same two books
for the same reasons.

The recheck also found two things the gate's own numbers hide. Three of the 23 marks are
small-caps glyphs whose records are correct, scored wrong because the review sheet shows the
character without the style. And two of the marks are real defects of a kind no shape-based flag
can catch.

## Method

Task 0 of the extraction plan re-measured the five books end to end at commit `f9fdfef`. That run
accepts 713 pages, versus 665 in the `alignment-t2-*` reports, so it is the first inventory built
on the alignment the band-identification fixes produce.

**Glyphs must be matched by page and box, not by line ordinal.** The band-identification fixes
change which bands a page yields, so `line_ordinal` is renumbered even for glyphs that did not
move. A first pass of this analysis matched on `line_ordinal` and reported four glyphs as removed
and a 16 percent pool turnover. Both were artifacts. Page plus box is stable, and
`source_line_ordinal` is stable as a secondary key.

That trap is easy to miss because the renumbering is small. Cell `e5` sits at `line_ordinal` 19
before the fixes and 21 after, with an identical box, character, flags, and `source_line_ordinal`
of 35.

The recheck located each of the 23 marked cells in the M15f inventory by the identity its review
CSV records, then carried it into the fresh inventory by page and box.

It then classified the survivors by `label_style` and by whether they carry one of the five
quality flags the filtered pass drops: `flat_ascender`, `overtall`, `narrow`, `wide`, and
`unlike_character`.

The recheck rendered the six cells that survive with no quality flag as images, at nine times
scale, and read them as images rather than as text. Each image showed every glyph box in the
containing word, with the full source line beside it. Reading them as text would have missed what
two of them are. The scripts are in `/workspaces/pdomain/.gate3-recheck/`.

## Evidence

### Every one of the 23 marks survives the band fixes

| bucket | count |
| --- | ---: |
| roman, carries a quality flag | 15 |
| roman, no quality flag | 4 |
| small caps, carries a quality flag | 2 |
| small caps, no quality flag | 1 |
| italic, no quality flag | 1 |
| removed by the band-identification fixes | 0 |

Seventeen of the 23 carry a quality flag, so the filtered pass drops them. The six that remain
match the `filtered_wrong` count of 6 that `gate3-review.json` already records. That is why the
filtered rate reaches 0.9942, with every book clear.

### The inventories barely moved, including in the failing books

| book | old glyphs | new glyphs | shared | Gate 3 sample pool retained | Gate 3 rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| projectID657550412c8dc | 91,560 | 89,751 | 89,739 | 0.980 | 1.0000 |
| projectID609bfa0449bdf | 70,267 | 70,267 | 70,267 | 1.000 | 0.9952 |
| projectID64a479f51ce5b | 52,487 | 52,487 | 52,487 | 1.000 | 0.9905 |
| projectID603d7d5e04ca0 | 28,564 | 29,427 | 28,527 | 1.000 | 0.9619 |
| projectID67a80fde44d34 | 23,638 | 22,534 | 22,426 | 0.951 | 0.9429 |

Counts are of distinct page-and-box-and-character identities. That merges duplicate boxes against
the raw row counts: 13 in `projectID657550412c8dc`, 13 in `projectID64a479f51ce5b`, and 7 in
`projectID609bfa0449bdf`, in both the old and the new inventory. The other two books have none.

Across these five books, churn does not track Gate 3 failure. `projectID603d7d5e04ca0` fails at
0.9619 while retaining its entire sampling pool. `projectID657550412c8dc` passes at 1.0000 having
lost 1,821 glyphs. The two books that fail sit at opposite ends of the retention range.

### The review sheet hides the style, so small caps score as errors

Three marked cells are `small_caps`. The clearest is cell `n16` in `projectID603d7d5e04ca0`, on
page `283.png`, in the word "Herring". The scan sets that word in small capitals. Every glyph after
the H is a small-capital form, and every one is labelled with its lowercase character and
`label_style: small_caps`.

That record is correct. Character and style together describe the ink exactly. The review sheet
renders the crop with the character alone, so the reviewer compares a small-capital N against the
letter `n` and marks it wrong.

Across the five books the pipeline applies `small_caps` to 877 glyphs, against 253,922 `roman`, 556
`italic`, and 2 `bold`. Those are frequencies, not an accuracy measurement. The style was verified
against the ink in one word only, where all seven glyphs agree.

### Two of the six unflagged survivors are real defects

Cell `s12` in `projectID67a80fde44d34` is a cut misalignment inside a word. In "times" the box
labelled `s` sits on the `e`, because the `m` box ends early and the `e` box is a 9-pixel sliver.

```
t 736-748  i 749-759  m 761-779  e 780-789  s 791-806
                      ^unlike_character  ^unlike_character  ^no flag
```

The `unlike_character` flag fires on the two glyphs whose crops are wrecked, but not on the one
that lands cleanly on the wrong letter.

Cell `e5` in `projectID603d7d5e04ca0` is a missed word gap in an italic face. The source line on
page `100.png` reads "While o'er the rock the fowler hung," in a script italic where letters join.
The gap between "the" and "fowler" is not found, so the three letters of "the" are cut across the
ink of both words. Cropping each box separately shows what each one holds.

```
labelled 't'  x649-689  holds "the"
labelled 'h'  x691-748  holds "fow"
labelled 'e'  x749-785  holds "ler"
```

The glyph labelled `e` is three letterforms from the following word.

The two are different failures that the flags miss for different reasons. `s12` is a well-formed
`e` wearing the label `s`, so nothing about its shape is wrong. `e5` is a three-letter chunk, which
`unlike_character` could in principle have caught and did not. What they have in common is only
that both crops sit on real ink at plausible cut boundaries, and both reach the filtered pass.

The other four unflagged survivors are `e13` and `h21` in `projectID603d7d5e04ca0` and `a10` in
`projectID67a80fde44d34`, plus `n16` above. Read at nine times scale with the whole word boxed, the
first three show the labelled character correctly cut: the `e` of "like", the `h` of "when", and
the `a` of "any". They warrant a second look by the owner rather than a claim from one reader.

## Conclusions

**Re-running the chain is not a route to closing Gate 3.** The band-identification fixes are worth
48 accepted pages and zero of the 23 mislabels. This closes the hypothesis carried in three
handoffs.

**Gate 3's 0.978 overstates the error rate.** Three of the 23 marks are small-caps records that are
correct. The gate measures the review sheet as much as it measures the inventory.

**Quality-flag filtering remains the lever that works,** catching 17 of the 23. That is arithmetic,
not a new finding: it restates the `filtered_wrong` count the review already recorded.

**Two unflagged survivors are real defects that the quality flags missed.** Cell `s12` is a
within-word cut misalignment that puts the label `s` on a well-formed `e`. Cell `e5` is a missed
word gap in a script italic that puts the label `e` on the three letterforms "ler". Neither carries
a quality flag, so both reach the filtered pass.

**Comparing two glyph inventories requires a stable key.** Match on page and box, or on
`source_line_ordinal`. Matching on `line_ordinal` silently reports unmoved glyphs as removed.

## Next steps

1. Show `label_style` on the Gate 3 review sheet, beside the character, and rescore.
2. Have the owner re-read `e13`, `h21`, and `a10` before treating them as review false positives.
3. Decide Gate 3 on the filtered inventory or on a stated lower number, with the small-caps
   correction applied first. The choice is unchanged by this finding; the number it is made against
   is not.
4. Measure how often a word gap is missed in italic and script faces, which `e5` shows is not
   covered by any current flag.

## What this does NOT establish

This does not rescore Gate 3. A rescore needs a fresh sample drawn from the fresh pool and a human
reading of the crops. The 23 cells were drawn from the old pool under seed `20260905`.

It does not establish that `e13`, `h21`, and `a10` are review errors. One reader looked at three
crops. That is evidence for a second look, not a verdict.

It does not measure how many small-caps glyphs a fresh sample would draw, so it does not say how
much of the 0.978 the correction recovers. It says only that three of 23 marks in this sample are
of that kind.

It does not test whether `label_style` is correct in general. The `small_caps` labels were checked
against the ink in one word, "Herring", where all seven glyphs agree. The 877-glyph count is a
frequency, not an accuracy.

It does not measure how common the `s12` and `e5` defects are. Two instances in a 1,050-cell sample
bound nothing; both were found because the review had already marked them.

It does not establish independence between churn and Gate 3 failure as a statistical result. Five
books, two of them failing, cannot support that. The claim is only that within this sample the two
do not move together, which is enough to retire the hypothesis that drove the re-run.

It says nothing about the `recognized` tier. Gate 3 samples `transcribed` only.

## Related

- [Per-book glyph inventory plan](../plans/2026-09-05-pgdp-per-book-glyph-inventory.md) — the live
  plan Gate 3 belongs to.
- [Glyph inventory architecture](../architecture/pgdp-glyph-inventory.md) — where the gate and the
  quality flags are defined.
- [Extraction plan](../plans/2026-09-06-extract-pgdp-measurement-library.md) — Task 0 captured the
  713-page inventories this recheck reads.
- [What word reconciliation still misses](2026-09-04-what-word-reconciliation-still-misses.md) —
  the earlier finding that a line-level metric overstates a per-unit error rate.
