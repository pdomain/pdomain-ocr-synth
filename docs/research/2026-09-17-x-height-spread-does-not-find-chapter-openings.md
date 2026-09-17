---
Status: active
Owner: CT
Created: 2026-09-17
Last verified: 2026-09-17
Kind: research
---

# X-Height Spread Finds Half the Chapter Openings, and Half of What It Finds Is Not One

## Agent Index

- **Kind:** research
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-17
- **Last verified:** 2026-09-17
- **Provenance:** measured on 2026-09-17 over the 1,040 pages carrying a recorded
  `line_x_height_spread_px` in the five `.m15f-evidence/inventory-projectID*` harvest manifests,
  by `/workspaces/pdomain/.m15f-evidence/xheight_spread_vs_page_class.py`, whose output is
  `/workspaces/pdomain/.m15f-evidence/xheight-spread-vs-page-class.json`; the origin of the
  disputed figure traced to `pdomain_pgdp_measure.glyphs._x_height_spread`'s docstring
- **Disposition:** Active finding. Settles the open question the split design raised against the
  "43 to 67 percent" figure. Changes how slice 4 should use the signal, and leaves one wrong
  docstring to correct in `pdomain-pgdp-measure`.
- **Read when:** designing the heading proposal, choosing a geometry signal for slice 4, or citing
  the x-height spread figure.
- **Search terms:** x-height spread, chapter opening, page_class, heading proposal, precision,
  recall, slice 4, mixed-size page, `_x_height_spread`.

## Recall is 50 percent, precision is 45 percent

At the recorded 8 px threshold, x-height spread catches 31 of the 62 chapter openings it could have
caught. Of the 69 pages it flags, 31 are chapter openings. That is 50 percent recall and 45
percent precision, pooled across the five books.

**The recorded "43 to 67 percent" is a precision figure, and it does not hold.** The
[split design](../specs/2026-09-06-measurement-labeling-synthesis-split-design.md) said the sentence
could be read either way and asked for a recomputation.

Reading the code settles the ambiguity, not recomputing. The docstring of `_x_height_spread` in
`pdomain-pgdp-measure/src/pdomain_pgdp_measure/glyphs.py` says "pages spreading more than 8 px are
43 to 67 percent chapter openings against a 2 to 7 percent base rate". That is precision measured
against a base rate.

Recomputed on the five books, per-book precision runs from 0 to 85 percent. Only two of
the five books land inside the recorded range, at 43 and 50 percent.

**The base-rate half of that docstring does hold.** Chapter openings are 3.6 to 7.3 percent of the
measured pages in the four books that have any. So a high-spread page really is several times more
likely to be a chapter opening than a page picked at random. The signal is not worthless. It is far
weaker and far less stable than the recorded figure claims.

**The pooled numbers hide the real problem, which is that the signal does not behave the same way
twice.** Per-book precision spans 0 to 85 percent and per-book recall 6 to 92 percent. A signal that
strong in one book and absent in the next cannot gate a proposal.

## What the five books actually show

| book | high-spread pages | chapter openings | both | precision | recall |
|---|---|---|---|---|---|
| `projectID603d7d5e04ca0` | 37 | 29 | 16 | 43% | 55% |
| `projectID609bfa0449bdf` | 2 | 16 | 1 | 50% | 6% |
| `projectID64a479f51ce5b` | 12 | 5 | 3 | 25% | 60% |
| `projectID657550412c8dc` | 13 | 12 | 11 | 85% | 92% |
| `projectID67a80fde44d34` | 5 | 0 | 0 | 0% | n/a |
| **pooled** | **69** | **62** | **31** | **45%** | **50%** |

High spread means `line_x_height_spread_px > 8`. Precision is the share of high-spread pages whose
`page_class` is `chapter_opening`; recall is the share of chapter openings that are high-spread.

The 1,040 pages with a recorded spread are the denominator. The other 327 pages record no spread;
317 of those are excluded pages.

The chapter-opening column counts only pages with a recorded spread, which is fewer than each book
holds in total. Across all 1,367 pages the five books carry 106 chapter openings; 62 of those have a
spread to test against.

## No variant of the calculation reproduces 43 to 67 percent

No variant of the calculation puts either rate in a 43-to-67-percent band, at any threshold. The
measurement script publishes the per-book precision and recall range for every combination of two
choices, at each of seven thresholds from 4 px to 20 px:

- strict `>` against inclusive `>=`
- excluding null-spread pages against counting them as low-spread

At 8 px, per-book precision spans 0 to 85 percent under all four variants. Per-book recall spans 6
to 92 percent when null-spread pages are excluded and 0 to 41 percent when they are counted as
low-spread. The full grid is under `per_book_rate_ranges_by_variant` in the JSON output.

## The two failures have different causes

**Recall fails because in two books the chapter openings are not mixed-size pages at all.** Compare
each book's chapter-opening spread against its other pages:

| book | chapter-opening spread (median) | other-page spread (median) |
|---|---|---|
| `projectID603d7d5e04ca0` | 16.0 px | 2.0 px |
| `projectID609bfa0449bdf` | 1.0 px | 1.0 px |
| `projectID64a479f51ce5b` | 13.0 px | 2.0 px |
| `projectID657550412c8dc` | 61.5 px | 1.0 px |
| `projectID67a80fde44d34` | none recorded | 2.0 px |

In three books the separation is enormous, a six- to sixty-fold gap between the two medians.

In `projectID609bfa0449bdf` there is no separation whatsoever. Its chapter openings sit at a median
spread of 1 px with a 90th percentile of 2 px, identical to its ordinary pages. So only 1 of its 16
chapter openings clears any useful threshold. Its chapter openings are also typeset at body size,
not merely uniform: their median x-height is 15.0 px, exactly the median of its other 237 measured
pages.

**Precision fails because a mixed-size page is often something other than a heading.** Of the 69
high-spread pages, 20 are `normal_recto`, 8 are `normal_verso`, and 10 are `unknown`. Mixed type
sizes mark plates, tables, footnote-heavy pages, and display matter as readily as they mark a
chapter opening. The signal measures what it says it measures; it is the inference to "heading" that
does not hold.

## A per-book threshold does not rescue it

Replacing the fixed 8 px cut with a per-book threshold of `median + 10 × MAD` over that book's own
spreads lifts pooled precision from 45 to 51 percent. Recall stays unchanged at 50 percent. At
`median + 6 × MAD` nothing moves at all: the thresholds it picks land at 7 or 8 px, so the result is
the fixed cut under another name. Both are computed in the script and reported under
`pooled_adaptive_threshold`.

The [word-gap finding](2026-09-03-word-gap-threshold-is-too-low.md) showed a fixed threshold
failing exactly this way, and a distribution-derived one fixing it. That fix does not transfer here.
The ceiling is the data: no threshold can find separation in a book whose chapter openings have
none.

## What slice 4 should do instead

**Do not gate the heading proposal on x-height spread.** Gating it costs half the chapter openings,
in exchange for a precision that is still close to a coin flip. In one of five books, it costs 15
of 16.

**Use spread as evidence that raises confidence, never as a precondition.** Where a page is already
`chapter_opening` and its spread stands far above its own book's median, the two signals agree and
the proposal deserves high confidence. Where the spread is ordinary, propose the heading anyway at
lower confidence and let a person decide. That is the two-tier discipline the
[synthesis design](../specs/2026-08-22-pgdp-typography-structure-synthesis-design.md) already
requires, applied to this signal.

**Record the book's own spread distribution in the proposal's evidence.** A reviewer looking at a
low-confidence heading in `projectID609bfa0449bdf` needs to know the signal is dead in that book,
not merely quiet on that page.

## What this measurement cannot tell you

**`page_class` is itself a machine proposal, not confirmed ground truth.** Every number here is
agreement between two automated signals, so it bounds how much spread adds over what `profile-pgdp`
already says, and nothing more. If `page_class` is wrong on a page, this measurement inherits the
error.

`projectID67a80fde44d34` is the clearest case. Across its 98 pages it carries only 2 chapter
openings, both on excluded pages with no recorded spread, so the 81-page analysis set contains none
at all. Its recall is undefined, and its 0 percent precision is a floor set by having no positives
to find, not a measurement of the signal.

Two chapter openings in a 98-page book is also low enough to suspect `page_class` rather than the
book. Confirming page kinds on that book would settle it, and the page-kind confirm route now exists
to do so.

## One docstring to correct

`_x_height_spread` in `pdomain-pgdp-measure/src/pdomain_pgdp_measure/glyphs.py` still states the 43
to 67 percent figure as measured fact, and that docstring is the origin of every other copy of the
claim. It should record what this recomputation found instead, or the next reader will rediscover
the same wrong number.

## How to reproduce this measurement

```bash
python3 /workspaces/pdomain/.m15f-evidence/xheight_spread_vs_page_class.py        # 8 px, the default
python3 /workspaces/pdomain/.m15f-evidence/xheight_spread_vs_page_class.py 12     # any other cut
```

It reads the five harvest manifests and prints the result. At the default threshold it writes
`/workspaces/pdomain/.m15f-evidence/xheight-spread-vs-page-class.json`, the artifact this document
cites. Any other threshold writes its own `-<threshold>` file instead, so a second run cannot
overwrite the numbers quoted here.

That JSON carries:

- the per-book and pooled rates
- each book's base rate
- the class mix of every high-spread page
- per-book and pooled threshold sweeps from 4 px to 20 px
- the two adaptive thresholds
- the four-variant grid this document cites

## Related

- [Measurement, labeling and synthesis split design](../specs/2026-09-06-measurement-labeling-synthesis-split-design.md)
  — raised the question this answers
- [The word-gap threshold is too low in every book](2026-09-03-word-gap-threshold-is-too-low.md) —
  the fixed-threshold failure whose fix does not transfer here
- [Labeling track roadmap](../plans/2026-09-07-labeling-track-roadmap.md) — where slice 4 sits
