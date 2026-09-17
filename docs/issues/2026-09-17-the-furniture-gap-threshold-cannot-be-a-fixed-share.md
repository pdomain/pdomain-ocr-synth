---
Status: implemented
Owner: CT
Created: 2026-09-17
Last verified: 2026-09-17
Kind: issue
Level: I2
---

# The furniture gap threshold is now fitted per book, because no fixed share worked

## Agent Index

- **Kind:** issue
- **Status:** implemented
- **Level:** I2
- **Last verified:** 2026-09-17
- **Resolution:** Fixed 2026-09-17 in `pdomain-ocr-labeler-spa` `6ed5156`. The threshold is fitted
  per book. One caveat remains, below.
- **Severity:** Low now, rising with volume — it costs some wrongly split or wrongly joined
  furniture regions per book, and a reviewer can fix each in one click
- **Affected version:** `pdomain-ocr-labeler-spa` at the merge of `feature/geometry-proposals`
- **Read when:** tuning the furniture detector, reviewing its first proposals, or adding a second
  geometry detector that needs a per-book threshold
- **Search terms:** FOLIO_GAP_SHARE_OF_TEXT_WIDTH, furniture gap, running head, folio, Otsu,
  per-book threshold, slice 4.

## What shipped

**The threshold is fitted to each book's own gaps, and fed the real gaps from the same six books it
lands strictly inside every valley.** Merged 2026-09-17 in `pdomain-ocr-labeler-spa` `6ed5156`, with
the suite green at 1692 passed and 4 skipped.

| book | fitted threshold | valley |
|---|---:|---|
| `projectID657550412c8dc` | 91.0 px | 64 to 118 px |
| `projectID609bfa0449bdf` | 129.0 px | 104 to 154 px |
| `projectID64a479f51ce5b` | 156.5 px | 136 to 177 px |
| `projectID3f1a5d4e86d06` | 158.5 px | 121 to 196 px |
| `projectID3fc3d7d03c613` | 137.0 px | 135 to 139 px |
| `projectID408c1dd9b9318` | 132.5 px | 130 to 135 px |

All six chose the fitted threshold; none fell back to the fixed share.

**It fits on OCR word boxes, not on image ink, and that corrects this issue's own first
recommendation.** The section below says the fit belongs in `measure_book`. It does not: that pass
discards each image after measuring it, so fitting there would decode every page a second time. The
detector already holds every page's word boxes, which are exactly what it splits. `FurnitureDetector`
pools every in-band word gap across the book, Otsu-splits them, and places the threshold at the
midpoint of the valley. It falls back to the fixed share when the book has fewer than 8 gaps, an Otsu
class has fewer than 2 members, or the fit lands outside 2 to 40 percent of the text width. Every
proposal's evidence records `gap_threshold_source` as `book_fit` or `fixed_share`.

**A detector opts into the whole-book step by subclassing `BookFittedDetector`.** It started as a
structural protocol, and review caught that `isinstance` would then match anything with a method
named `fit`, including a scikit-learn-style model.

**One caveat remains.** Two books have valleys only 4 and 5 px wide, `projectID3fc3d7d03c613` and
`projectID408c1dd9b9318`. The fit is correct on their ink gaps, but the margin is thin, and word-box
gaps differ slightly from ink gaps. Recheck those two once a book has been through OCR in the labeler.

## The finding

`furniture_region_detector` splits the words in a page's top furniture band wherever the horizontal
gap exceeds 10 percent of the book's fitted text width. Measured across six books, **10 percent
falls inside the correct range in none of them.**

The gap distribution inside a furniture band is strongly bimodal: word spaces on one side, the gap
between a running head and its folio on the other, with a wide empty valley between. The valley is
easy to find. It just is not in the same place twice.

| book | text width | valley, as a share of text width | 10 percent lands |
|---|---:|---|---|
| `projectID657550412c8dc` | 864 px | 7.4% to 13.7% | inside |
| `projectID609bfa0449bdf` | 793 px | 13.1% to 19.4% | below |
| `projectID64a479f51ce5b` | 866 px | 15.7% to 20.4% | below |
| `projectID3f1a5d4e86d06` | 1095 px | 11.1% to 17.9% | below |
| `projectID3fc3d7d03c613` | 1596 px | 8.5% to 8.7% | above |
| `projectID408c1dd9b9318` | 1240 px | 10.5% to 10.9% | below |

The six valleys do not share a common point. Their lower bounds run from 7.4 to 15.7 percent and
their upper bounds from 8.7 to 20.4 percent, so the intersection is empty. No constant can sit
inside all six.

## What it costs today

The error is small in most books and real in one. Against the Otsu split on each book's own gaps,
the 10 percent constant makes 58 splits where 57 are right, 67 where 65 are right, and 95 where 109
are right. That last book, `projectID3fc3d7d03c613`, loses 14 splits: 14 running heads that stay
joined to their folio and reach a reviewer as one wrong region instead of two right ones.

## The fix, and it is the one the word-gap finding already established

Derive the threshold from each book's own gap distribution rather than fixing it. An Otsu split over
the pooled gaps finds the valley cleanly in all six books. This is the same fix, and the same
method, that the
[word-gap finding](../research/2026-09-03-word-gap-threshold-is-too-low.md) applied to word
segmentation, where a fixed threshold was wrong in every book and a distribution-derived one lifted
reconciliation from 0.208 to 0.800 in the worst.

**The measurement pass is where it belongs.** `measure_book` already decodes every page and holds
each page's ink bands and grayscale threshold, which is everything the calculation needs. Fitting
the gap threshold there, and carrying it on `MeasuredBook` through to `DetectorInput`, keeps the
detector a pure per-page function and costs no second image pass.

**One caveat on the measurement.** These numbers come from ink runs projected out of the page image,
not from OCR word boxes, because no stored word geometry exists for these books. The detector
clusters word boxes. The two should agree closely, since a word box is drawn around its ink, but the
fit should be rechecked against word boxes once a book has been through OCR in the labeler.

## Reproducing this

```bash
cd /workspaces/pdomain/pdomain-ocr-labeler-spa
./.venv-container/bin/python /workspaces/pdomain/.m15f-evidence/furniture_band_gap_threshold.py 3 80
```

It measures the first three corpus books at 80 pages each and writes
`/workspaces/pdomain/.m15f-evidence/furniture-band-gap-threshold.json`. Pass different arguments for
a different book count and page count. The three aligned books in the table above were measured the
same way against `projectID657550412c8dc`, `projectID609bfa0449bdf` and `projectID64a479f51ce5b`.

## Related

- [Geometry region proposals design](../specs/2026-09-17-geometry-region-proposals-design.md) — the
  design that named this threshold an unsettled starting value.
- [Geometry region proposals plan](../plans/2026-09-17-geometry-region-proposals.md) — the plan that
  shipped the constant.
- [The word-gap threshold is too low in every book](../research/2026-09-03-word-gap-threshold-is-too-low.md)
  — the same failure and the same fix, one level down.
