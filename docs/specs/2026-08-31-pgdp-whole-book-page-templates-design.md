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

Front matter and plates are deliberately absent. Front matter has no measured discriminator, and one
illustration is too little to separate a plate from a table with tall bands. Both fall to `unknown`,
which suppresses nothing, so neither omission costs anything today. The two front-matter pages seen
so far, `a005.png` at +76 and `118.png` at +111, land in the trough and behave correctly there.

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
residual is at most `max(HEAD_WINDOW_MINIMUM_PX, 3 x deviation)` px, where the minimum is 8, and its
text-block left edge is within the same bound of the template's.

How steady a book's first band must be is a separate question from how far one page may sit from it,
and the two bounds must not be confused. Running heads were measured 0 to 4px off their book's
median, while the nearest page whose first band is genuine text sat 76px below. A 2px window would
have left `p179.png` unclassified and therefore still misaligned. The share of pages joining a normal
template is flat between a 4px and a 20px window on all three steady books, so the choice inside that
range does not matter; 8 is double the observed spread and an order of magnitude clear of text. A
page joins the chapter-opening template when it has no band inside the normal
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

- Page class is one of `normal_recto`, `normal_verso`, `chapter_opening`, or `unknown`.
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
- What separates front matter, plates, advertisements, and indexes from each other and from the
  trough. All currently fall to `unknown`.
- What bounds a page's residual against the chapter-opening template. Residuals are tight in two
  books, with medians of 11px and 2px, and scattered in a third at 224px. Nothing depends on the
  bound yet, because `chapter_opening` suppresses no band.
- Whether page class belongs in `pgdp-profile/v2` or in a separate report, given that
  `pgdp-profile/v1` must stay byte-compatible.

## Revision, 2026-08-31: two fitting defects found on whole books

Three of the five review books classify almost nothing, and the two reasons are unrelated. Together
they cost 61 of 367 accepted pages and every one of the 18 errors in the measured precision ledger.

### The side split must come from geometry, not the file name

Deciding recto from the trailing digits of the file name fails whenever a book does not number its
files by folio. `projectID657550412c8dc` names pages at ten times the folio, so `p1720.png` is page
172 and `p1350.png` is page 135. The last digit is then almost always zero, 291 of its 298 pages
read as verso, and the split collapses.

The damage follows from the collapse. That book's text-block left edge is genuinely bimodal, with
127 pages near 120 and 121 near 185. A single pooled template takes 123, which sits about 60px from
one of the real modes, so the 8px edge test rejects nearly every page. The book classifies 27 of
312 despite a first-band deviation of 1.0, which is as steady as the best book in the set.

Group the normal pages by their text-block left edge instead, and label the two groups by the
majority file-name parity within each. Geometry is what the template stores and what classification
tests, so geometry is what should define the grouping. The file name keeps only the naming job it
can still do.

This also corrects a number in the table above. The 6px recto-verso shift recorded for In a German
Colony compared 7 pages against 291, so it described the broken split rather than the book.

### The deviation ceiling refuses books whose head wanders

A ceiling of 2px assumes a head that barely moves. Two books have a head that is clearly present and
clearly periodic, but noisy: `projectID603d7d5e04ca0` at a deviation of 18.5 and
`projectID67a80fde44d34` at 16.0. Both are refused outright and classify nothing.

Chapter openings are not the cause. Excluding every sunk page moves the two figures only to 16.0 and
14.5.

Raise the ceiling to 25. The window formula stays `max(8, 3 x deviation)`, so the widest window a
qualifying book can produce is 75px, which stays below the 76px at which genuine top-of-page text
begins. A book at a deviation of 26 is still refused, because its window would cross that line.

Be honest about what this admits. These two books put 6 percent and 10 percent of their pages within
2px of the book median, against 90 percent for Dead Men's Shoes. Their heads are real but unsteady,
and their windows will run near 48px, leaving about 28px of margin rather than the 72px a steady
book enjoys. The ledger after this change is what tells us whether that margin holds.

## Revision, 2026-08-31: band 0 is not always the running head

The classifier read `ink_bands[0]` as the page's running head. That is wrong whenever a fleck of
dust holds an ink band of its own above the head, and it answers the open question this design
carried about pages that start above their book's median. Such a page is junk above furniture, and
the two cases need separating rather than choosing between.

The profile keeps the speck because it cannot see it. Its wire format carries `y_start` and `y_end`
and nothing else, so the ink share the aligner uses to drop dust is not available at classification
time. Height cannot stand in for it either: `f005.png` opens with a 9px roman folio that is a
genuine head, while the speck on `166.png` is 5px.

Position can. A speck sits higher than anything the press printed, so the first band at or below
`center - window` is the first that can be type. `_head_band_ordinal` returns that band, the class
is decided from its top, and every ordinal down to and including it is named as furniture. Where
band 0 already is the head the result is unchanged, which is every page but a handful.

The failure had two shapes. On `166.png` the speck sat 63px above the book median, so the page fell
outside the head window, classified `unknown`, suppressed nothing, and let a body source line bind
to the head. On `p003.png` the speck sat close enough to the median that the page still classified,
and ordinal 0 then suppressed the speck while the head below it stayed live. Both are the same
assumption failing.

Across the five review books this moved 35 pages from `unknown` into a real class and moved none the
other way.

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
