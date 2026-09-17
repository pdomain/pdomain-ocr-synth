---
Status: active
Owner: CT
Created: 2026-09-17
Last verified: 2026-09-17
Kind: research
---

# Bottom-of-page furniture is too rare, and sits too close to the text, to detect by geometry

## Agent Index

- **Kind:** research
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-17
- **Last verified:** 2026-09-17
- **Provenance:** measured 2026-09-17 over all 1,385 pages of the five baseline corpus books by
  `/workspaces/pdomain/.m15f-evidence/bottom-furniture/` (`measure_bands.py`, `ocr_bands.py`,
  `analyze_bottom.py`, per-book band JSON, `summary.json`), which re-measures each page with
  `measure_image_snapshot`, `fit_book_templates` and `classify_pages`, reads the bottom bands with
  Tesseract because proofed text drops this furniture, and checks a seeded 100-page sample and all
  97 automatically flagged pages by eye
- **Disposition:** Active finding. Answers the roadmap's bottom-of-page furniture candidate with a
  no, and records what a later pass would need.
- **Read when:** considering a footer, catchword, signature mark or press figure proposal, or
  mirroring `furniture_band_ordinals` for the bottom of the page.
- **Search terms:** bottom furniture, footer, catchword, signature mark, press figure, drop folio,
  footnote detection, direction line, furniture_band_ordinals.

## Do not build a bottom-furniture detector from geometry

Bottom marks are rare, and nothing sets them apart from the surrounding text. Across 1,328 eligible
pages, only 88 carry a confirmed bottom mark, 6.6 percent. Top-of-page furniture is far more
common: it covers 1,089 of 1,385 pages, 78.6 percent.

The best rule for finding bottom marks works by position rather than by a gap. It scores 0.52
precision and 0.80 recall pooled, raising 71 false alarms against 78 real marks. The top-furniture
rule that splits the header from the folio does much better: it gets 17 of 17, 20 of 20 and 22 of
23 pages right on real books.

**The signal that works at the top of the page does not exist at the bottom.** The head detector
splits a furniture band from the body by a gap fitted per book. Bottom marks do not have that gap;
they sit at ordinary line spacing. 81 of the 88 sit within 1.25 line pitches of the last body line,
with a median of 1.05. Only 32 pooled pages have a short last band set off by 1.5 pitches or more.

## The marks are signature marks, drop folios and press figures

The 88 confirmed marks are 57 signature marks, 17 drop folios and 14 probable press figures.

**There are no catchwords at all** in these five books, which are 19th and 20th century. A
catchword proposal has nothing to train or test against here.

**Bottom folios appear on one book, and only on chapter openings.** All 17 are drop folios on
chapter opening pages of `projectID657550412c8dc`. No `normal_recto` or `normal_verso` page in any
of the five books carries a bottom folio. If a bottom page-number proposal is ever built, it should
be limited to chapter openings, which is exactly where top furniture proposes nothing.

**Marks are unevenly spread.** By book: 35, 29, 19, 5 and 0. The book with none is table-heavy.

## Footnotes need more than geometry

Footnote blocks appear on 89 of the pooled last bands. The best rule tested uses a gap of at least
two line leadings plus smaller type below it. It scores 0.50 precision and 0.74 recall on one book,
and 0.76 precision and 0.52 recall on another. Its thresholds were chosen on the same pages that
scored it, so those numbers are optimistic.

**X-height does not separate footnotes from body text.** In `projectID64a479f51ce5b` the footnote
and body x-heights are both 1.08 of the book median.

**The false alarms are ordinary typesetting:** stanza breaks, speaker labels, a last line without
ascenders, and lines such as "END OF PART FIRST".

## A position rule beats a gap rule, and still fails on two books

The position rule flags a mark under two conditions. The last band must start no higher than 0.25
pitch above the book's median body bottom, and it must be shorter than 0.8 of a body band height.
This rule finds 20 of 20 marks with 3 false positives in one book, 28 of 29 with 13 in another, and
6 of 7 with none in a third.

The rule fails on two books. On the poetry book it finds 23 marks, misses 17 and raises 40 false
positives. On the table-heavy book it finds no real mark at all and raises 16 false alarms; its
single flagged page is a table rule.

The reason is the body bottom itself. Its median absolute deviation is 4 to 11 pixels in four
books, and 53 pixels in the poetry book, whose pages end where the stanza ends.

## A later pass would need four things

- **Books with catchwords**, which means earlier printing than this corpus.
- **The word text, not just the band.** Which mark it is comes from reading it: a folio from the
  page sequence, a signature from its 16-page stepping and letter pattern, a press figure from
  recurrence. One book's direction line spans 0.76 of the text width and needs the same horizontal
  split the top furniture detector already does.
- **A smaller ink filter.** The 60-pixel speck filter drops real signature letters, confirmed by eye
  in `projectID603d7d5e04ca0`, so every count here is a lower bound.
- **A bottom band mirror in the profile,** if this is revisited. It would need band bottoms in
  `_PageGeometry`, a body-bottom median and deviation in `fit_book_templates`, and bottom ordinals
  from `_classify_page`, all in `pdomain-pgdp-measure`'s `page_templates.py`. The profile drops each
  band's x-extent and ink count today, and a bottom detector would need both.

## The evidence here is thin in four places

- Press figures rest on one book and one numeral, identified by recurrence.
- Footnotes rest on two books and 94 truth pages, most of them a single line reading "* See page N."
- Drop folios rest on one book.
- Mark recall is estimated from the signature period, not counted.

## Related

- [Geometry region proposals](../specs/2026-09-17-geometry-region-proposals-design.md) — the top
  furniture detector this would have mirrored.
- [Labeling track roadmap](../plans/2026-09-07-labeling-track-roadmap.md) — where bottom furniture
  was listed as a candidate.
