---
Status: active
Owner: CT
Created: 2026-09-18
Last verified: 2026-09-18
Kind: research
---

# Ragged right finds poetry; nothing geometric finds blockquote

## Agent Index

- **Kind:** research
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-18
- **Last verified:** 2026-09-18
- **Provenance:** measured 2026-09-18 over the five aligned corpus books the bottom-furniture note
  used (1,385 pages) by `/workspaces/pdomain/.m15f-evidence/poetry-blockquote/`
  (`measure_blocks.py`, `analyze_blocks.py`, `blocks.json`, `summary.json`). Reuses
  `../bottom-furniture/bands-<project>.json`, the ink-band geometry the bottom-furniture study
  already measured with pdomain-pgdp-measure's own `measure_image_snapshot`, `fit_book_templates`,
  and `classify_pages`; this note does not re-measure any image. Every geometric signal is checked
  against real ground truth: each book's own PGDP `rounds/F2.json` formatting-round text, whose
  `/* ... */` and `/# ... #/` markup independently marks poetry and block-quote spans, on the 801
  of 1,193 usable pages (67.1 percent) where that text's line count matches the measured ink-band
  count exactly.
- **Disposition:** Active finding. Corrects slice 6's stated reason for poetry: a working
  geometric rule exists, built on raggedness rather than indent. Leaves blockquote's geometric
  separability an open question — the corpus does not carry enough confirmed examples to answer
  it.
- **Read when:** designing the poetry or blockquote region proposal, deciding whether slice 6
  needs a vision-language model or a cheaper text-only classifier, or citing the claim that
  geometry cannot separate poetry from blockquote.
- **Search terms:** poetry, blockquote, block quote, ragged right, justified, indent, slice 6,
  vision-language model, VLM, region proposal, capital-initial rule, F2 formatting markup.

## Geometry does separate poetry, just not by the signal the roadmap named

[The labeling track roadmap](../plans/2026-09-07-labeling-track-roadmap.md) defers poetry against
blockquote to slice 6, a vision-language model, because "geometry cannot separate the cases." That
claim was never tested. It is wrong for poetry.

Right-edge raggedness measures how much a block's lines scatter at the right edge, instead of
lining up at a shared margin. It separates poetry from everything else at 87.5 percent precision
and 93.3 percent recall, pooled across the five-book corpus. That is a real, working geometric
rule, and it is stable: precision stays between 83 and 88 percent across a threshold range spanning
more than sevenfold. That stability is a very different picture from the earlier finding that
x-height spread swings from 0 to 85 percent precision per book (see
[x-height spread does not find chapter openings](2026-09-17-x-height-spread-does-not-find-chapter-openings.md)).

But indent, the signal the roadmap actually tabled for poetry ("indent, ragged right, lines short
against the page's measured text width"), is not what does the separating. Most poetry blocks in this corpus
are *also* indented on both sides by a naive test, simply because verse lines usually fall short of
the full measure. That overlap is exactly why the roadmap's two rules collide when read literally. Its
tabled poetry rule and its tabled blockquote rule ("indent both sides, with leading before and
after") both fire on the same blocks, unless raggedness is added as the tiebreaker. More on that
below.

**Blockquote has no working geometric signal in this corpus.** The best rule found — a block
indented on at least one side, with a consistent (justified) right edge — scores 2.3 percent
precision and 47.7 percent recall.

Confirmed blockquote spans are also rare: only 44 in the 801-page ground-truth subset (of 1,385
pages total), and they are a mixed bag — letters, stage directions, a chapter-summary header, a
dateline — not a single consistent typographic shape. Many carry no indent and no unusual leading
at all.

This note cannot say blockquote has no geometric signature; 44 examples is too few to rule
that out. It can say plainly that no geometric rule tested here finds one, and the specific rule the
roadmap proposed does not work.

**A one-line text rule beats every geometric signal tested, for poetry.** Checking whether each
line of a block starts with a capital letter — the English-verse convention of capitalizing every
line, regardless of where a sentence falls — scores 95.4 percent precision and 96.3 percent recall
pooled. No vision model, and no language model, is needed to reach that number. See "Can a person
tell from the text alone," below.

## The corpus and how it was measured

The corpus is the same five aligned PGDP books used in
[the bottom-furniture note](2026-09-17-bottom-of-page-furniture-is-too-rare-and-too-close-to-the-text.md):
1,385 pages total, of which 1,193 carry a known `page_class`. The other 192 pages are `unknown`
and excluded — the same exclusion every measurement in this workspace applies when it depends on
`page_class`.

`measure_blocks.py` reuses the bottom-furniture study's own cached ink bands — one row-projection
band per printed line, with its left edge, right edge, and vertical extent — rather than
re-measuring any page image. Those bands already came from pdomain-pgdp-measure's
`measure_image_snapshot`, `fit_book_templates`, and `classify_pages`. For each page, it drops
furniture bands and specks — the same rule the furniture study used: under 60 foreground pixels or
under 7 pixels tall. Then it groups the remaining lines into text blocks. A block boundary falls
wherever the gap between two consecutive lines exceeds 1.5 times the book's own median single-line
gap.

For each block it measures:

- **Left indent and right indent** — the block's median line edge against the book's fitted
  `text_left_px`/`text_right_px` for that page's `page_class`, as a fraction of the book's fitted
  text width. A block counts as indented on a side once that fraction passes 0.03 (roughly one em
  in these books).
- **Right-edge raggedness** — the median absolute deviation of the lines' right edges, as a
  fraction of text width. A block counts as ragged once that fraction passes 0.008. That threshold
  sits in a genuinely empty gap in the data. Prose-labeled blocks have a right-edge deviation
  whose 90th percentile is 0.003 of text width; poetry-labeled blocks have a 10th percentile
  of 0.012, with nothing in between 0.003 and 0.012 to argue over. The two populations' medians
  differ fortyfold: 0.001 for prose versus 0.041 for poetry.
- **Leading before and after**, in units of the book's median single-line gap.

Where a page's F2 formatting text splits into exactly as many non-blank lines as the page has
kept ink bands, `measure_blocks.py` zips each line to its band. It then reads off the PGDP-marked
span state — poetry, blockquote, or ordinary prose — and assigns each block the majority label of
its lines. That line-for-line match holds on 801 of the 1,193 usable pages, 67.1 percent. The other
third mostly fails in the two books with heavy footnotes and tables, where a footnote's text sits
at a different position in the F2 file than its physical band on the page. Every ground-truth
number in this note comes from that 801-page subset; `analyze_blocks.py` produces the full
breakdown as `summary.json`.

## What the corpus contains

| | count |
|---|---:|
| total pages, five books | 1,385 |
| pages with known `page_class` (used) | 1,193 |
| pages where F2 text lines up 1:1 with ink bands (ground-truth usable) | 801 (67.1% of used) |
| text blocks segmented | 5,614 |
| single-line blocks (raggedness cannot be measured on one line) | 1,916 (34.1%) |
| multi-line blocks | 3,698 (65.9%) |
| aligned blocks carrying a PGDP ground-truth label | 3,593 |
| — of those, labeled poetry | 1,135 |
| — of those, labeled blockquote | 44 |
| — of those, labeled ordinary prose | 2,414 |

One book, `projectID603d7d5e04ca0`, is almost entirely poetry — its title page reads "St Baldred of
the Bass, and Other Poems" — and it carries 724 of the corpus's 748 confirmed multi-line poetry
blocks. Every pooled number in this note is, in large part, a statement about that one book. The
per-book tables below show where the signal holds up once that book is set aside.

| book | pages used | indented-left | indented-both | confirmed poetry blocks | confirmed blockquote blocks |
|---|---:|---:|---:|---:|---:|
| `projectID603d7d5e04ca0` (the poetry book) | 374 | 71.9% | 68.0% | 724 | 16 |
| `projectID609bfa0449bdf` | 300 | 16.8% | 13.3% | 1 | 3 |
| `projectID64a479f51ce5b` (the table-heavy book) | 198 | 33.4% | 28.6% | 14 | 1 |
| `projectID657550412c8dc` | 249 | 12.4% | 4.6% | 8 | 17 |
| `projectID67a80fde44d34` | 72 | 80.7% | 79.8% | 1 | 0 |

(Confirmed-block counts are multi-line, aligned, ground-truthed blocks — the population raggedness
can actually be tested against.) Blockquote evidence is nearly split between two books: 17 confirmed
blocks in `projectID657550412c8dc` and 16 in the poetry book itself, `projectID603d7d5e04ca0`.
Even the corpus's blockquote ground truth is not free of the one book that dominates everything
else in this note. `projectID64a479f51ce5b` is the same table-heavy book the furniture note found geometry
struggling with.

## Indent alone is a smear, not a cluster — and raggedness is what separates the two

Across the ground-truthed blocks, the two geometric axes behave very differently.

**Left indent and right indent, taken as plain position, do not cluster cleanly by category.**
Prose-labeled blocks sit close to the margin (median left indent 0.005 of text width, 90th
percentile 0.043). Poetry-labeled blocks sit further in (median 0.067, 90th percentile 0.156).
Blockquote-labeled blocks sit in between (median 0.035, 90th percentile 0.165) — overlapping both
neighbors.

On the right side the overlap is worse: poetry's median right indent is 0.242, more than
40 times prose's 0.006, because verse lines routinely fall short of the measure. Blockquote's
median right indent is 0.005, statistically the same as ordinary prose. A rule that calls "indented
on both sides" a sign of blockquote will catch poetry far more often, because poetry is the category
that is actually indented on the right in this corpus, not blockquote.

**Right-edge raggedness cleanly separates poetry from everything else**, at the 87.5
percent precision / 93.3 percent recall reported above. Classifying each block by two independent
questions — is it indented, and is its right edge ragged or justified — gives this cross-tabulation
against ground truth (aligned blocks, both single- and multi-line, with unmeasurable single-line
blocks counted as justified by convention):

| ground truth | flush | left-indented, justified | left-indented, ragged | both sides, justified | both sides, ragged | right side only | total |
|---|---:|---:|---:|---:|---:|---:|---:|
| prose | 1,671 | 133 | 3 | 387 | 41 | 179 | 2,414 |
| poetry | 6 | 14 | 2 | 347 | 472 | 294 | 1,135 |
| blockquote | 16 | 17 | 0 | 4 | 2 | 5 | 44 |

Two things fall out of this table:

- **Poetry is overwhelmingly in the "ragged" columns** (472 + 294 + 2 of 1,135, 68 percent), and
  almost never in the "justified, indented" column that a naive blockquote rule would flag (347 of
  1,135, but those are mostly poetry too, not blockquote).
- **Blockquote is spread thin across every column**, including 16 blocks that are flush with the
  ordinary body margin and carry no indent at all. There is no column blockquote dominates.

## The "matches both" count the roadmap's rules produce, and why it mostly resolves

Reading the roadmap's two rules completely literally and independently — poetry is "indented,
ragged right"; blockquote is "indent both sides" — 834 of the 5,614 blocks (14.9 percent) satisfy
both at once. That looks like a large population needing a model to break the tie.

It mostly is not one. Of the 515 of those 834 blocks with a confirmed ground-truth label, 472 are
poetry, 41 are ordinary prose, and only 2 are blockquote.

The overlap is an artifact of an underspecified blockquote rule. The roadmap's tabled blockquote
signature never says the block must also have a *consistent* right edge — yet a genuinely
block-quoted passage (reflowed prose, not verse) should have one. Add that qualifier and the two
categories become mutually exclusive by construction, because ragged and justified cannot both be
true of the same block. The ambiguous population the roadmap worried about mostly evaporates once
the missing qualifier is made explicit.

That is not a free win for blockquote, though. Adding "and justified" to the blockquote rule is
exactly the rule that was tested above and scored 1.2 percent precision, 5.4 percent recall. Making
poetry and blockquote geometrically distinct from each other does not make blockquote itself
findable — see the numbers below.

## Every rule tested, scored against ground truth

| rule | precision | recall | true / false positive / false negative |
|---|---:|---:|---|
| ragged right alone, no indent required — vs. poetry | 87.5% | 93.3% | 698 / 100 / 50 |
| indented left AND ragged (the roadmap's literal poetry rule) — vs. poetry | 91.2% | 63.4% | 474 / 46 / 274 |
| indented on both sides (the roadmap's literal blockquote rule) — vs. blockquote | 0.6% | 10.8% | 4 / 673 / 33 |
| indented on both sides AND justified — vs. blockquote | 1.2% | 5.4% | 2 / 160 / 35 |
| indented on either side AND justified, best variant found — vs. blockquote | 2.3% | 47.7% | 21 / 881 / 23 |
| each line starts with a capital letter (text only) — vs. poetry | 95.4% | 96.3% | 720 / 35 / 28 |

Requiring indent in addition to raggedness *raises* poetry's precision slightly, from 87.5 to 91.2
percent, but *costs* a third of its recall, from 93.3 to 63.4 percent. Indent is adding noise, not
signal, exactly as the smeared indent distributions above predict.

Every blockquote variant tried tops out under 3 percent precision. Loosening from "both sides" to
"either side" only trades a little recall for a lot more noise.

## Raggedness is stable across a wide range of thresholds

The 0.008 cut is not doing all the work by itself. Sweeping it from 0.004 to 0.030 — a sevenfold
range — keeps precision between 83 and 88 percent while recall trades off gradually as the
threshold tightens:

| threshold (right-edge MAD, fraction of text width) | precision | recall |
|---:|---:|---:|
| 0.004 | 83.2% | 96.9% |
| 0.006 | 86.1% | 95.3% |
| 0.008 | 87.5% | 93.3% |
| 0.010 | 87.5% | 91.7% |
| 0.015 | 87.2% | 86.6% |
| 0.020 | 86.5% | 80.2% |
| 0.030 | 84.3% | 67.0% |

That stability is the opposite of what the earlier x-height finding showed, where per-book
precision ranged from 0 to 85 percent depending on the book. Raggedness does not behave that way —
but the next section shows why the pooled number still needs a caveat.

## The pooled number is mostly one book — the other four are thin evidence

Splitting precision and recall by book tells a less flattering story than the pooled 87.5 percent:

| book | confirmed poetry blocks | true / false positive / false negative | precision | recall |
|---|---:|---|---:|---:|
| `projectID603d7d5e04ca0` (the poetry book) | 724 | 675 / 37 / 49 | 94.8% | 93.2% |
| `projectID609bfa0449bdf` | 1 | 1 / 5 / 0 | 16.7% | 100.0% |
| `projectID64a479f51ce5b` | 14 | 14 / 6 / 0 | 70.0% | 100.0% |
| `projectID657550412c8dc` | 8 | 7 / 45 / 1 | 13.5% | 87.5% |
| `projectID67a80fde44d34` | 1 | 1 / 7 / 0 | 12.5% | 100.0% |

The capital-initial text rule shows the same pattern:

| book | true / false positive / false negative | precision | recall |
|---|---|---:|---:|
| `projectID603d7d5e04ca0` (the poetry book) | 703 / 8 / 21 | 98.9% | 97.1% |
| `projectID609bfa0449bdf` | 1 / 1 / 0 | 50.0% | 100.0% |
| `projectID64a479f51ce5b` | 8 / 1 / 6 | 88.9% | 57.1% |
| `projectID657550412c8dc` | 7 / 24 / 1 | 22.6% | 87.5% |
| `projectID67a80fde44d34` | 1 / 1 / 0 | 50.0% | 100.0% |

Recall stays high everywhere; precision does not.

In the poetry book, both rules score 95 to 99 percent precision (94.8 percent for raggedness,
98.9 percent for the capital-initial rule) on hundreds of confirmed examples. That is well above
the 87.5 percent pooled figure quoted earlier, which blends this book's strong result with the
other four books' weaker ones.

In the other four books — the "ordinary book with an occasional embedded stanza" case that slice
6's own example is actually about — there are only 22 confirmed poetry blocks total (1 + 14 + 8 + 1
across the four books). Precision on that handful swings from 12.5 to 88.9 percent. That is thin
evidence, the same caliber of thin as the furniture note's press-figure and drop-folio findings.

This note is confident poetry separates geometrically within a book that is mostly verse. It is not
confident the same precision holds for a book that only occasionally quotes a poem.

## How rare poetry and blockquote pages are

Pooled across all five books, 27.8 percent of aligned pages carry a confirmed poetry block and 4.2
percent carry a confirmed blockquote block. That is dominated by the one poetry book. Excluding it,
across the other four books (564 aligned pages), 4.3 percent of pages carry a confirmed poetry
block and 3.2 percent carry a confirmed blockquote block.

That sits much closer to
[the furniture note's rare bottom-furniture case](2026-09-17-bottom-of-page-furniture-is-too-rare-and-too-close-to-the-text.md)
(6.6 percent of pages) than its common top-furniture case (78.6 percent of pages). In an ordinary
book, poetry and blockquote are both uncommon page-level events, and roughly matched in rarity to
each other. Slice 6's example is not a rare edge case dressed up as common — but it is not frequent,
either.

## Can a person tell from the text alone

Four examples from the sampled blocks make the case concretely.

**A drama scene that PGDP's own `/# ... #/` markup calls a "blockquote," which reads as verse on
sight.** From `projectID603d7d5e04ca0`, page `210.png`: "I'll perish sooner!-- / [Attempts first to
stab herself, then the King; but is prevented by the Guards; upon which she throws away the
dagger, and sobs more in anger than in grief. / Oh! Heaven! forgive the deed! / Misfortune thus
makes cowards of us all." (The source text has an opening bracket around the stage direction with
no closing bracket, a common PGDP proofing artifact; it is reproduced here exactly as measured.)
This is blank-verse stage dialogue from a closet drama embedded in the poetry book.

PGDP's convention tags the whole scene — dialogue plus stage directions — as a non-reflowing block
because it should not be reflowed into a paragraph. That is not because a proofreader would call it
"a block quotation" in the ordinary sense. A reader sees dramatic verse immediately; the
ground-truth label itself is the noisier signal here.

**A centered stanza number that looks blockquote-shaped by geometry.** Text such as "XIII." or "V."
sitting alone between stanzas has both margins pulled far in, since it is short and centered — the
same shape a naive rule expects from an indented, justified quotation. The text gives it away at a
glance as a section number, something geometry alone cannot do.

**A real blockquote with no indent at all.** From `projectID64a479f51ce5b`, page `p199.png`: "I beg to
express my great obligation to your Lordship for so complete a determination to obtain justice for
me as you have exhibited..." This is quoted correspondence, set flush with the ordinary body margin.
Nothing marks it as a blockquote except the surrounding context — that it is a letter being quoted.
Neither geometry nor a simple text rule can see that without reading the paragraph around it.

**A short poem stanza that geometry misses but the capital rule catches.** "Yet deem not aught but
virgin love / That bosom e'er could venture in," is only two lines, too short for the raggedness
measure to trip reliably. Every line still starts with a capital letter, and the verse rhythm is
unmistakable even without context.

For poetry, OCR text alone — even a single-line rule with no model at all — outperforms every
geometric signal tested here.

For blockquote, the ground truth is too sparse and too varied (a letter, a stage direction, a
chapter-summary header, a dateline) for this note to say text alone would settle it. That needs
its own investigation with more confirmed examples than this corpus supplies.

## What this settles, and what it does not

Geometry separates poetry from prose and from blockquote, cleanly, through right-edge raggedness —
not through the indentation the roadmap named. That corrects the roadmap's mechanism, not just its
conclusion.

Geometry does not separate blockquote from anything in this corpus. The evidence is too thin — 44
confirmed spans across five books — and too varied in shape to say whether a better geometric rule
exists, or whether blockquote genuinely has no geometric signature. That is a "the corpus cannot
fully answer this" finding for blockquote specifically, not a confident no.

The roadmap's stated reason for slice 6 was that "geometry cannot separate the cases, poetry
against blockquote being the standard example." That reasoning is wrong for poetry, where a
working, threshold-stable geometric rule exists. It is unproven either way for blockquote.

A much cheaper approach is worth trying before a vision-language model. For poetry, that could be
a text rule as simple as checking capitalized line starts — or, short of that, a plain language
model reading OCR text with no image input at all. Blockquote needs more labeled data before any
rule, geometric or model-based, can be evaluated honestly.

## Related

- [Labeling track roadmap](../plans/2026-09-07-labeling-track-roadmap.md) — where slice 6 defers
  poetry against blockquote to a vision-language model on the grounds this note tests.
- [Bottom-of-page furniture is too rare, and sits too close to the
  text](2026-09-17-bottom-of-page-furniture-is-too-rare-and-too-close-to-the-text.md) — the corpus
  and evidence-directory convention this note follows, and the page-level rarity framing it
  borrows.
- [X-height spread does not find chapter openings](2026-09-17-x-height-spread-does-not-find-chapter-openings.md) —
  the per-book honesty framing and threshold-sweep method this note follows.
