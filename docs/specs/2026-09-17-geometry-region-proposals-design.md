---
Status: active
Owner: CT
Created: 2026-09-17
Last verified: 2026-09-17
Kind: spec
---

# The geometry engine already runs, and slice 4 is mostly a matter of keeping its output

## Agent Index

- **Kind:** spec
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-17
- **Last verified:** 2026-09-17
- **Provenance:** measured 2026-09-17 by
  `/workspaces/pdomain/.m15f-evidence/furniture_band_coverage.py`, whose output is
  `/workspaces/pdomain/.m15f-evidence/furniture-band-coverage.json`, and by
  `page_class_confidence_on_furniture.py` beside it; and authored from direct
  inspection of `pdomain-pgdp-measure`
  `page_templates.py`, `profile_models.py`, `profiling.py`; `pdomain-ocr-labeler-spa`
  `core/jobs/handlers/propose_page_kinds.py`, `core/jobs/handlers/propose_regions.py`,
  `core/regions/detector.py`, `core/regions/block_adapter.py`, `core/project_state.py`,
  `api/dependencies.py`; `pdomain-book-tools` `ocr/block.py`; and the 2026-09-17 recomputation of
  the x-height spread figure
- **Disposition:** Active. Slice 4 of the labeling track. Neither open decision blocks a plan:
  the persisted-measurement record is contingent on a performance problem that has not happened,
  and the cluster-gap threshold has a stated direction the plan can settle.
- **Read when:** designing or building the region proposal engine, choosing which region roles a
  machine may propose, or deciding where a proposal run gets its geometry.
- **Search terms:** slice 4, geometry engine, region detector, RegionDetector, BookTemplates,
  PageClassification, furniture_band_ordinals, ink bands, page furniture, running head, folio.

## What this settles

Slice 4 does not need a new measurement pipeline. The labeler already measures every page of a
book and fits the book's own page shapes. It then keeps three numbers per page and discards the
rest. Slice 4 keeps what it discards and turns that into region proposals.

It also settles the first region roles a machine should propose. Those are the page furniture at
the top of each page: the running head and the folio. They are the highest-volume, least ambiguous
regions in any book. No ground truth for them exists anywhere in the suite.

## The measurement slice 4 needs is already computed and thrown away

`propose_page_kinds` calls `profile_page` on every page of the book. It fits the book's templates
with `fit_book_templates`, then classifies each page with `classify_pages`. It keeps three numbers
per page: the class, its confidence, and its template residual. Everything else it measured is
dropped. What it drops carries every geometry signal the roadmap's slice 4 table asks for.

`BookTemplates` holds the book's fitted page shapes. Each `PageTemplate` in it carries
`first_band_top_px`, `first_band_spread_px`, `text_left_px`, `text_right_px`, and `band_count`. An
indent and a ragged right edge are both measured against those text edges. The edges are fitted per
book, from the book's own pages. That per-book fit is the one thing a fixed threshold can never be.

`PageClassification` holds each page's class, its `template_residual_px`, its `confidence`, and
its `furniture_band_ordinals`. That last field names which of the page's ink bands are furniture
rather than text. It is the one field the page-kind run does not keep. The same confidence reaches
`PageMeasurement` as `page_class_confidence`.

`PageMeasurement` holds each page's `ink_bands`, `margins`, `foreground_bounds`, and
`derived_estimates`. The ink bands are a row projection of the page image, so they see rules,
illustrations, and printed marks that carry no words at all. The OCR word tree cannot see marks like
that.

Building a second measurement path in the labeler would duplicate all of this and then disagree
with it.

## Ink bands give vertical structure and the page gives horizontal structure

An `InkBand` is `y_start` and `y_end` and nothing else. It is a horizontal row projection, so it
knows where ink sits down the page and knows nothing about where it sits across the page.

Every horizontal signal therefore comes from the page's own word boxes, which the labeler already
holds as a `pdomain_book_tools.ocr.page.Page`. Indent, ragged right, line length against the book's
measured text width, and the gap between a running head and a folio on the same band are all
per-word-box measurements.

A region proposal needs both. A band gives a proposal its vertical extent. The words inside that
band give it its horizontal extent and its box.

## Start with page furniture, because it is the only class with no ground truth anywhere

The first detector should propose `page header` and `page number` from the top furniture bands.
Four facts make that the right first target.

- **The signal is already computed.** `furniture_band_ordinals` is every band from the top of the
  page down to and including the running-head band. Nothing is printed above the head, so the
  classifier can say this without ambiguity, and it already does. In the five books, every page
  with a furniture band is a `normal_recto` or a `normal_verso`. No chapter opening or unclassified
  page has one. That is what the classifier's own code says it should do.
- **The class is high volume, measured.** 1,089 of the 1,385 pages in the five aligned corpus books
  carry a top furniture band, which is 78.6 percent, running from 71.4 to 89.4 percent per book.
  All but 30 of those pages carry exactly one band. This counts bands the classifier calls
  furniture by their position, not bands whose content has been read. So the number bounds the
  opportunity. It does not prove each one holds a running head. Under the rule below, one band
  proposes one or two regions. So these five books hold on the order of 1,100 to 2,200 furniture
  regions to confirm or reject. No other region class will produce a corpus at that rate.
- **It is unambiguous to a reviewer.** A person confirming a running head is answering a question
  with one right answer. Poetry against blockquote is not, which is why the roadmap defers that to
  a model in slice 6.
- **Nothing else in the suite can produce this ground truth.** PGDP F2 transcription strips running
  heads and page numbers entirely, so all page furniture is `recognized` tier and never
  `transcribed`. It has no ground-truth text and Gate 3 has never measured it. The labeler is the
  only thing in the workspace that can label it.

## A furniture band becomes one or two regions, not one

Hierarchy rule 3 of the [region vocabulary](2026-09-07-region-vocabulary-design.md) says a running
head and a page number are always separate blocks, even when they sit on the same physical line.
The band gives one y range. The words in it decide how many regions come out of it.

Cluster the words in the band by horizontal gap. One cluster is one region. A wide run of words
proposes `page header`. A short isolated cluster that is entirely digits or roman numerals proposes
`page number`. A cluster that is neither proposes `page header` at lower confidence. A running head
is the more common of the two, and a reviewer can correct it in one click.

This is the same rule the band analysis already applies vertically, applied horizontally, and it
needs no new measurement.

## Confidence comes from the cluster's shape, and the page fit goes in the evidence

**A furniture proposal must not inherit its page's classification confidence.** This design first
said it should, and measurement says that is wrong.

`_confidence_from_residual` in `pdomain-pgdp-measure` scores a page as
`max(0.0, 1.0 - residual_px / max(first_band_spread_px, 8))`. Over the 1,089 pages carrying a
furniture band across the five corpus books, the template residual is 8 px or more on 288 of them,
which scores exactly 0.0 at any fitted spread of 8 or less. That is 26 percent of furniture pages
pooled. Per book it is 73 percent in `projectID603d7d5e04ca0` and 67 percent in
`projectID67a80fde44d34`, against 0 to 1 percent in the other three.

The error is one of kind, not calibration. `classification.confidence` answers how well a page fits
its book's fitted template, which is a page-class question. It does not answer whether a band is a
running head. A page whose head band sits 40 px below the book's median still has a head band; the
head is just lower. Inheriting that score would hand a quarter of all furniture proposals a
confidence of exactly zero, and two thirds of them in two books, so slice 5's confidence-ranked
queue would bury the proposals a person most needs to see.

**Score from the cluster's own shape instead.** Three cases, in descending order of how much the
geometry says:

- **A numeric cluster isolated in a furniture band scores highest.** Two signals agree: the
  classifier called the band furniture, and the cluster reads as a folio.
- **A wide cluster sharing a band with something else scores next.** The band is furniture and this
  is the part of it that is not the folio.
- **A lone non-numeric cluster scores lowest.** It could be a running head, or the top line of body
  text under a band the classifier misplaced.

**Those three numbers are uncalibrated, and the design should say so rather than imply otherwise.**
No region ground truth exists anywhere in the suite, so there is nothing to calibrate against. The
first review pass in slice 5 is what sets them, and until then they encode an ordering the geometry
justifies rather than a measured accuracy.

**Carry the page fit in the evidence.** `page_class_confidence` and `template_residual_px` belong in
every proposal's evidence dict. A reviewer and slice 5 both need to see how well the page fits its
book, without that fit being allowed to zero out a good proposal.

Two further rules follow from what has been measured.

- **Never gate a proposal on x-height spread.** The recorded figure claiming 43 to 67 percent of
  high-spread pages are chapter openings is wrong. Recomputed, precision is 45 percent pooled and
  0 to 85 percent per book, at 50 percent recall, and in one of five books the chapter openings show
  no elevated spread at all. Spread may raise a heading proposal's confidence and must never decide
  one. See
  [x-height spread does not find chapter openings](../research/2026-09-17-x-height-spread-does-not-find-chapter-openings.md).
- **A page the classifier declined to classify gets no furniture proposals.** When
  `fit_book_templates` finds a book whose first band wanders, it returns no templates at all rather
  than widening the window until everything classifies. A detector must honour that refusal.
  `furniture_band_ordinals` is empty for an unclassified page and for a chapter opening, and empty
  means propose nothing, never "guess from the top band".

## The detector seam has to widen, and it should widen to a fitted book

`RegionDetector` is `Callable[[Page], Sequence[DetectedRegion]]` today. A furniture detector cannot
work through it. It needs the page's index to find that page's classification. It also needs the
book's templates to know where the head band belongs.

Widen the seam to take one input object carrying the page, its index, its classification, and the
book's fitted templates. The detector stays a plain callable and stays swappable through
`JobRunner.context["region_detector"]`, exactly as Task 5 built it.

This mirrors the shape `propose_page_kinds` already uses: fit the whole book once, then judge each
page against the fit. It is the same two-phase structure, and slice 4 should not invent a second
one.

## The measurement has to reach the run, and there are two ways

A `propose_regions` run needs each page's `PageMeasurement` and the book's `BookTemplates`. The
page-kind run computes both. Getting them to the region run is the one genuine design choice here.

**Re-measure inside the region run.** Call `profile_page` over the book again and re-fit. It is
simple and it is always fresh. It costs a second full-book image decode per run, which is the
expensive part of the page-kind job.

**Persist the measurement when the page-kind run computes it.** Write `BookTemplates` and each
page's `PageClassification` into a journal beside the page-kind proposals, and have the region run
read it. It costs one file and a staleness question: a run that reads a stale measurement must be
able to say so.

**I recommend re-measuring, and I first argued the opposite.** The argument for persisting rested
on the page-kind journal already tracking what a run was conditioned on. It does not.
`PageKindProposalRun` carries only `run_id`, `model_id`, `model_version`, `created_at` and
`page_count`. The per-facet digests live on the region `ProposalRun` alone. They record what the
region run read, not whether a stored measurement is still good for the page it was taken from.

Persisting therefore means designing a new record. That record carries the measurement plus the
image digest it was measured from, and a rule for what a region run does when the digests disagree.
This is a design of its own, and it is not paid for by machinery that already exists.

Re-measuring is correct by construction and costs one image pass inside a background job that is
already offloaded off the event loop. Take the simple path first. Revisit it if measurement time
turns out to be the bottleneck. If it does, the persisted record should carry its own image digest,
so the staleness rule needs nothing from the page-kind journal.

## A book-scoped job can take verified page leases, and should

A run on a book-labeling project reads `project.image_paths` directly today, bypassing the manifest
hash pin, which is filed as a defect against `propose_page_kinds`. The provenance design lists this
as unsettled: "How a book-scoped proposal run reaches pages, given that the book labeling manifest
is read-only today and has no write path anywhere in the labeler."

The machinery already exists. `ProjectState.open_labeling_page(page_index)` opens a caller-owned
verified lease without a request context and without touching global state. `bind_labeling_page`
binds it to the current context, so `labeling_image_path` resolves to the sealed descriptor.
`api/dependencies.bind_page_labeling_lease` does exactly this per request, and
its own docstring says background jobs acquire their own lease separately. The session caches at
most three page images, so a book-scoped loop holds one page at a time.

Both proposal runs should take a lease per page rather than refusing to run or reading unpinned
bytes. Refusing would mean page kinds and regions never work on book-labeling projects, which are
the projects the whole labeling track exists for.

## What slice 4 does not build

- **No model.** Slice 4 is geometry and nothing else. Poetry against blockquote, and every other
  case geometry cannot separate, waits for slice 6.
- **No bottom-of-page furniture.** `furniture_band_ordinals` covers the top bands only, because the
  classifier derives it from the running-head band and nothing is printed above that. A page
  footer, a catchword, a signature mark, and a press figure all sit below the text block and need
  the mirror of the same logic. That is a bounded follow-on, not part of the first detector.
- **No braced sets.** `BlockCategory` has `BLOCK`, `PARAGRAPH`, and `LINE`, and no `GROUP`.
  Hierarchy rule 6 also requires a new `_sort_items` branch that orders members before their label.
  The `brace`, `bracket`, and `group label` roles stay out of reach until that lands in
  `pdomain-book-tools`.
- **No automatic `page number` from PP-DocLayout.** `PP_DOCLAYOUT_TO_PGDP` maps the native
  `page_number` label to `footer`, so the answer is deleted before it reaches a block role. Slice 4
  does not depend on that path: it proposes the folio from band geometry and word shape instead.
  The mapping is still worth fixing, and it is still three edits in two repos.

## What this design does not settle

One thing is still open: **what a persisted measurement record looks like**, if re-measuring turns
out to be too slow. That record needs the measurement, the image digest it was taken from, and a
rule for what a region run does when that digest no longer matches the page. A journal beside the
page-kind proposals is the obvious home and is not the only one.

The cluster-gap threshold this section used to leave open has since been measured, and it is now a
filed issue rather than a design question. The shipped detector splits at a fixed 10 percent of the
book's fitted text width. Across six books the correct range differs in every one, and the six
ranges have no common point, so no fixed share can work. An Otsu split over each book's own gaps
finds it cleanly every time, which is the fix the word-gap finding already established one level
down. See
[the furniture gap threshold cannot be a fixed share](../issues/2026-09-17-the-furniture-gap-threshold-cannot-be-a-fixed-share.md).

## Related

- [Region provenance and persistence](2026-09-07-region-provenance-and-persistence-design.md) — the
  design this builds on, and the source of the open item on how a book-scoped run reaches pages.
- [Region vocabulary](2026-09-07-region-vocabulary-design.md) — the 34 roles and the hierarchy
  rules this design obeys.
- [Region routes and proposal run](../plans/2026-09-08-region-routes-and-proposal-run.md) — Task 5
  built the detector seam this design widens.
- [Labeling track roadmap](../plans/2026-09-07-labeling-track-roadmap.md) — where slice 4 sits.
- [X-height spread does not find chapter openings](../research/2026-09-17-x-height-spread-does-not-find-chapter-openings.md)
  — why the heading signal cannot gate a proposal.
