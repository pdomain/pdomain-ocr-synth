# PGDP Whole-Book Page Template Design

## Agent Index

- **Kind:** spec
- **Status:** draft
- **Owner:** CT
- **Created:** 2026-08-31
- **Last verified:** 2026-08-31
- **Provenance:** measured on 2026-08-31 from whole-book profiles of four PGDP books, the fixed
  25-page M15b review set, and owner direction in this session
- **Disposition:** Active design for whole-book page templates and page classification.
- **Read when:** implementing page classification, running-head suppression, or book-level geometry.
- **Search terms:** PGDP, M15a, type page, page template, running head, chapter opening, recto,
  verso, page class.

M15a will measure each book's type page from every page it has, then classify each page against a
small set of templates. M15b will read the class and stop matching running heads to source lines.

## What the classification must achieve

Stop the aligner from binding a source line to page furniture, and give later measurement stages a
book-level geometry they can trust.

## Why the aligner needs this

Running heads and page numbers are printed on the page but deleted from the F2 text. PGDP proofers
strip them, so every such band is a line candidate with no source line to match.

The aligner has no way to know that. When a page's candidate count equals its eligible
source-line count, the monotone path is forced to match the running head to source line 0.
Every match below it then inherits the shift.

That is not hypothetical. Of the five pages accepted in the 2026-08-31 review, `p008.png` and
`p179.png` are both shifted this way. All 66 of their matches are wrong. Accepted-line precision
is about 62 percent against a 98 percent gate. The other three accepted pages skip their running
head and align correctly.

Whether a page skips or steals is luck. `p006.png`, `p008.png`, and `p155.png` come from one book
and carry the same running head. Two skip it and one does not.

## Why the type page is the right prior

A letterpress book is set once. The type page holds its position across the whole volume, so a
band's distance from the top of the page says what the band is.

Measured against each book's modal first-band position. The classifier uses the median rather
than the mode. The two agree on every book that qualifies, and differ only where no template is
fitted:

| book | pages | head y | within 2px | recto/verso shift | measure | sunk pages |
|---|---|---|---|---|---|---|
| Dead Men's Shoes vol. I | 308 | 71 | 90% | 61px | 792 / 787 | 22 |
| The Royal Mint | 230 | 67 | 78% | 0px | 867 / 867 | 13 |
| In a German Colony | 295 | 111 | 76% | 6px | 876 / 862 | 27 |
| St Baldred of the Bass | 426 | 129 | 9% | 46px | 929 / 936 | 182 |

In three of the four books the first band lands within two pixels of the same y on more than three
quarters of pages. That single number separates the cases nothing else could.

Against that same modal position, every page whose first band is a running head sits on or beside
it. Every page whose first band is genuine text sits far below:

| page | first band y | book modal y | offset | first band is |
|---|---|---|---|---|
| `p006.png` | 67 | 67 | +0 | running head |
| `p008.png` | 67 | 67 | +0 | running head |
| `089.png` | 129 | 129 | +0 | running head |
| `p148.png` | 73 | 71 | +2 | running head |
| `p155.png` | 69 | 67 | +2 | running head |
| `p179.png` | 75 | 71 | +4 | running head |
| `a005.png` | 147 | 71 | +76 | dedication text |
| `118.png` | 240 | 129 | +111 | title text |

Running heads span 0 to 4 pixels of offset and genuine text starts at 76. Nothing falls between.

## The page templates

A book is described by a small set of measured templates rather than one type page.

- **Normal recto** and **normal verso**, which differ only by the binding shift.
- **Chapter opening**, whose text block starts lower and which carries no running head.
- **Front matter**, such as a title page, dedication, or contents.
- **Plate or illustration**, whose ink does not form regular bands.

Chapter openings are as regular as body pages. In Dead Men's Shoes they sink by a repeated amount.
`p060`, `p094`, `p140`, and `p208` all start 296px below the modal position, and `p024` and `p273`
start 236px below. They also hold fewer bands, 18 to 22 against a body mode of 24 to 27.

## Recto and verso are separate templates

The folio sits on the outer edge, so the text block shifts with the binding margin. Dead Men's Shoes
moves 61px between the two, at a constant measure of 792 against 787. The Royal Mint moves nothing.

Because the shift is real in some books and absent in others, it must be measured per book. A single
template averaged across both would place the head box wrong on half the pages of any book that
shifts.

## The fit score decides whether to trust the templates

St Baldred of the Bass is the warning. Only 9 percent of its pages sit near the modal head position
and 182 of 426 read as sunk. It is verse with notes, so it has no single stable text block.

Books like it are over-represented in this corpus, because M14 ranks a book higher when its
typography is varied. The pilot books are disproportionately the ones a single type page cannot
describe.

So each template carries the share of pages that fit it, and each page carries its own residual. A
book whose templates fit poorly falls back to per-page handling, and its pages are classified
`unknown` rather than forced into a template. Observation stays separate from inference, as it
already does elsewhere in the profile.

### How fit is computed

Reuse the `median-mad/v1` method the profile already applies to pooled estimates. For a book, take
the median first-band `y_start` across every page that has bands, and the median absolute deviation
from it.

That deviation is the whole test. It is 0px in Dead Men's Shoes, 1px in the Royal Mint, and 1px in
In a German Colony. It is 18.5px in St Baldred of the Bass.

A book has a usable type page when its first-band deviation is at most `HEAD_MAD_MAXIMUM_PX`, which
is 2. Otherwise every page in it is classified `unknown` and M15b suppresses nothing.

That value sits inside an observed gap. Across 41 books profiled whole, 30 have a deviation of 0px
or 1px and the next book up is at 2.5px. No book measured between 1 and 2.5. The books below the
line hold their first band within two pixels of the median on 59 to 99 percent of pages; the books
above it manage 9 to 50 percent.

Do not use a tolerance scaled from the deviation as the test on its own. Scaling widens with the
disorder it is meant to detect. At three times its deviation, St Baldred admits 81 percent of its
pages inside a 55px window, which classifies nothing.

Within a fitting book, a page's residual against a template is the absolute difference between its
first-band `y_start` and the template's, in pixels. A page joins a normal template when that
residual is at most `max(2, 3 x deviation)` px and its text-block left edge is within the same bound
of the template's. A page joins the chapter-opening template when it has no band inside the normal
head window and its first band lies at least `CHAPTER_SINK_MINIMUM_PX` below the median, which is
150.

Across the 8,162 pages of the 30 qualifying books, offsets from the median cluster at both ends and
thin out between. Pages sitting 0 to 10px below the median account for 16.8 percent, and pages 201
to 500px below account for 4.4 percent. The 51 to 200px range holds 1.5 percent, spread over three
times the width.

A page landing in that thin range is classified `unknown` rather than forced into either template.
The range is a trough, not a gap, so a page inside it is genuinely ambiguous and M15b suppresses
nothing on it.

### What the profile records

Each book gains its templates and each page gains a class.

- Page class is one of `normal_recto`, `normal_verso`, `chapter_opening`, `front_matter`, `plate`,
  or `unknown`.
- Each template records its first-band `y_start`, text-block left and right edges, modal band count,
  the number of pages assigned to it, and their share of the book.
- Each book records `first_band_mad_px` and the share of its pages that are not `unknown`.
- Each page records `page_class` and `template_residual_px`.

Every one of these is an observation or a count, so it carries the existing `truth_class` and
`confidence_kind` fields rather than a new confidence scheme.

## Whole books, not samples

Profiling costs 9.5ms per page. One 312-page book profiles in 3 seconds, and all 73,103 pages of the
local corpus would take about 12 minutes. There is no reason to estimate a book's type page from a
sample when every page is affordable.

This does not change M15b's per-page processing. The templates are precomputed numbers, so the
aligner still decodes one scan at a time and stays snapshot-safe.

## What M15b consumes

The profile gains a page class and the book gains its templates. M15b reads the class and suppresses
the bands the template marks as furniture, so no candidate is emitted for a running head or a folio.

The alignment report records which template matched and its residual, so an incorrect suppression
stays visible as evidence rather than disappearing.

## Non-goals

- This design adds no OCR engine. Every measurement above comes from ink-band geometry, and the
  M15b design forbids an OCR dependency.
- It does not read folio digits or running-head text.
- It does not use adjacent pages. Confirming a chapter opening from a short preceding page, and
  resolving a word split across a page break, both need consecutive pages. The fixed 25-page
  selection does not contain them.
- It does not rectify, rotate, or dewarp scans.
- It does not change any M15b quality gate or alignment threshold.

## Open questions

- How many templates a book needs before the set stops paying for itself.
- Whether a page starting above its book's median is furniture or junk. A quarter of pages in
  qualifying books sit above it, most by a pixel or two, but the tail reaches 64px. The two examples
  seen so far are a 3px speck and a table rule, which are different defects with the same
  measurement.
- Whether the six page classes cover plates, advertisements, and indexes, or need more.
- Whether page class belongs in `pgdp-profile/v2` or in a separate report, given that
  `pgdp-profile/v1` must stay byte-compatible.

## Adversarial Review

- **Stage and source:** One read-only reviewer checked this design against the M15b and v2 extractor
  designs, the profile models, the extractor, and the whole-book profile JSON the numbers come from.
- **Accepted findings:** The offsets were measured against the median of five sampled pages per book
  while the table beside them used whole-book modes. Every offset is recomputed here against the
  whole-book mode, which moves `p179.png` from +0 to +4 and `118.png` from +107 to +111. The fit
  score and page class named no formula, unit, or field, so an implementer could not act on them;
  both are now specified.
- **Effect on this document:** The offsets became their own table with both baselines shown, and the
  fit computation and recorded fields became their own sections.
- **Residual risks:** `HEAD_MAD_MAXIMUM_PX` and `CHAPTER_SINK_MINIMUM_PX` are unset. Four books are
  too few to fix either, and both are algorithm constants that a later change would version. The
  page classes are proposed from four books and may not cover plates, advertisements, or indexes.

## Where the measurements come from

Whole-book profiles of four PGDP books, produced on 2026-08-31 and kept in
`/workspaces/pdomain/.m15b-evidence/`. The precision and header-steal findings come from the fixed
25-page review set reproduced the same day, read against the source text and the rendered overlays.
