# Remaining work

## Agent Index

- **Kind:** plan
- **Status:** active
- **Owner:** CT
- **Created:** 2026-05-05
- **Last verified:** 2026-11-06
- **Provenance:** rewritten 2026-11-06 from the plans still on disk and from code checks in this repository and its
  sibling packages. Shipped behavior is in `docs/architecture/`.
- **Disposition:** The live index of work that is not finished.
- **Read when:** asking what is still open.
- **Search terms:** remaining work, roadmap, M11, M12, labeling track.

## Goal

This index names only the work that is still open.

Each item is one line and includes the path of its plan or issue.

## Architecture

Shipped behavior is [Development and recipe system](../architecture/development-and-recipe-system.md),
[Output and publishing](../architecture/output-and-publishing.md), and
[Measurement and labeling live in other repositories](../architecture/measurement-and-labeling.md).

## Tech Stack

This package is Python 3.13, uv, pytest, Ruff, and basedpyright.

The open preview UI has no chosen stack in code yet.

Labeling work that is still open lands in `pdomain-ocr-labeler-spa`, `pdomain-book-tools`, or `pdomain-book-contracts`,
not here.

## Global Constraints

A plan stays in `docs/plans/` until its code and tests show it is finished.

Partial plans stay even when most of their tasks have shipped.

## Still open in this repository

- Bootstrap left two files unwritten: there is no `LICENSE` file and no `DEVELOPMENT.md`.
  [docs/plans/00-bootstrap.md](00-bootstrap.md)
- Corpus providers that ship are local, web, and Wikisource. Further providers stay deferred.
  [docs/plans/03-corpus.md](03-corpus.md)
- Rendering still has deferred font-coverage and sampling work. [docs/plans/05-rendering.md](05-rendering.md)
- Degradation still has optional stages, including perspective and bleed-through. They are not a public extension
  contract. [docs/plans/06-degradation.md](06-degradation.md)
- Detection publishing is ImageFolder. Parquet sharding is not built.
  [docs/plans/09-detection-mode.md](09-detection-mode.md)
- Stretch still has extra recipes, cloud rendering, and live statistics. [docs/plans/10-stretch.md](10-stretch.md)
- The preview UI is not built. NiceGUI is not the direction. [docs/plans/11-preview-ui.md](11-preview-ui.md) and
  [docs/plans/11-preview-ui-scoping.md](11-preview-ui-scoping.md)
- Glyph-annotation emission is not built. Nothing in `src/` writes `glyph_annotations`.
  [docs/plans/12-glyph-annotations.md](12-glyph-annotations.md)

## Still open, with the code in another repository

- Explicit membership and matching: `matcher.py` and `tests/ocr/test_sibling_region_membership.py` are not in the
  sibling trees.
  [docs/plans/2026-09-08-explicit-membership-and-matching.md](2026-09-08-explicit-membership-and-matching.md)
- Word and glyph provenance: `test_words_ground_truth_provenance.py` and `test_glyph_mark_staleness.py` are absent.
  [docs/plans/2026-09-08-word-and-glyph-provenance.md](2026-09-08-word-and-glyph-provenance.md)
- Style-span review: no `StyleSpanDecisionLog`.
  [docs/plans/2026-09-08-style-span-review-surface.md](2026-09-08-style-span-review-surface.md)
- Editorial corrections: no `EditorialCorrection` type.
  [docs/plans/2026-09-08-editorial-corrections.md](2026-09-08-editorial-corrections.md)
- Labeling slices 6 and 7 are not built. Drawing or resizing a region is not built. Slice 6 lost poetry as its example.
  [docs/plans/2026-09-07-labeling-track-roadmap.md](2026-09-07-labeling-track-roadmap.md)

## Page-kind confirm and save_page

- Page-kind confirm requires the event store. Without one, it returns 503. `save_page` still allows a store-less save.
  The five defects in the same file are fixed.
  [docs/issues/2026-09-16-page-kind-follow-ups-parked-during-tasks-6-and-7.md](../issues/2026-09-16-page-kind-follow-ups-parked-during-tasks-6-and-7.md)

The issue index is [One issue is still open](../issues/README.md).

## Not this repository's remaining work

Open measurement gates, including glyph Gate 3, live with `pdomain-pgdp-measure`. The note is
[the Gate 3 recheck](../research/2026-09-07-gate3-recheck-on-the-713-page-alignment.md).
