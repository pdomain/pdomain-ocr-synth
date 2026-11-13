# This repository renders synthetic OCR training pairs from recipes

## Agent Index

- **Kind:** context
- **Status:** active
- **Owner:** CT
- **Created:** 2026-07-14
- **Last verified:** 2026-11-12
- **Provenance:** rewritten 2026-11-06 from the tree at `aaecea1` plus inspection of sibling packages. The long PGDP run
  digest that this file held through `aaecea1` stays in that commit. Research notes below keep the measurements that
  still matter. Current region-editing and layout-training status checked against sibling code on 2026-11-07.
  The image pipeline was recorded in architecture on 2026-11-12, and the open list was consolidated into the roadmap.
- **Disposition:** Injected operational ground truth.

Measurement and human labeling are in other packages. See
[Measurement and labeling live in other repositories](../architecture/measurement-and-labeling.md).

This repository has shipped recipe discovery, validation, rendering, recognition and detection output, and Hugging Face
publishing.

The contracts are [Development and recipe system](../architecture/development-and-recipe-system.md),
[Synthesis pipeline](../architecture/synthesis-pipeline.md), and
[Output and publishing](../architecture/output-and-publishing.md).

## What is still open

The schedule is the [roadmap](../plans/README.md).

Work whose code belongs in this repository includes the unfinished preview UI, glyph-annotation
emission, and the deferred corpus, transform, rendering, and degradation names listed there.

Matching, provenance, style-span review, editorial corrections, and the layout-model backend
belong in the labeler, the contracts package, or `pdomain-ocr-training`. The roadmap names the home
for each.

Manual region drawing, resizing, and member-word editing ship in the labeler. Layout training has an export loader
and an injected-model loop in `pdomain-ocr-training`; it has no default model backend.

## GitHub Actions workflows are gone

Commit `0068970` on 2026-09-13 removed the GitHub Actions workflows, including the weekly dep-refresh workflow.

`just ci` is the local gate.

## Where the old measurement numbers are

The ranking, alignment, typography, and glyph-inventory runs are no longer this package's behavior.

These notes still hold the measurements:

- [Gate 3 recheck](../research/2026-09-07-gate3-recheck-on-the-713-page-alignment.md)
- [Word-gap threshold](../research/2026-09-03-word-gap-threshold-is-too-low.md)
- [What word reconciliation still misses](../research/2026-09-04-what-word-reconciliation-still-misses.md)
- [F2 line-break hyphens](../research/2026-09-03-pgdp-f2-line-break-hyphens.md)
- [Bottom-of-page furniture](../research/2026-09-17-bottom-of-page-furniture-is-too-rare-and-too-close-to-the-text.md)
- [X-height spread](../research/2026-09-17-x-height-spread-does-not-find-chapter-openings.md)
- [Ragged right and blockquote](../research/2026-09-18-ragged-right-finds-poetry-blockquote-has-no-geometric-signature.md)

One ranking result from the old digest is not in those notes.

Two `rank-pgdp` runs over `/workspaces/pdomain-data/pgdp-corpus` were byte-identical. The two runs used project limit 50
and 12 pages per project.

The corpus had 286 projects. Of those, 285 were rankable.

The report selected 600 pages.

The top five scores were:

1. `projectID64a479f51ce5b` 487
2. `projectID62930b71a45bb` 479
3. `projectID5dc798788ade0` 471
4. `projectID63161caf7eafa` 438
5. `projectID657550412c8dc` 438

## Page kind and the labeled-dataset contract are undecided

Whether every mutation should refuse, or the UI should hide confirm, is open.

The page-kind confirm route returns 503 when no event store is wired. `save_page` still treats a missing store as a
clean in-memory save.

The issue is [page-kind follow-ups](../issues/2026-09-16-page-kind-follow-ups-parked-during-tasks-6-and-7.md).

The labeled-dataset contract this repository would consume is still unspecified.

Whether the labeler ingests PGDP corpora directly is still unspecified.

See the [split design](../specs/2026-09-06-measurement-labeling-synthesis-split-design.md).
