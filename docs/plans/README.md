# Roadmap

## Agent Index

- **Kind:** plan
- **Status:** active
- **Owner:** CT
- **Created:** 2026-05-05
- **Last verified:** 2026-11-12
- **Provenance:** rewritten 2026-11-12 from the plans and specs still on disk, the architecture
  notes, and the sibling packages named below. Shipped image-pipeline behavior was checked
  against source the same day and recorded in `docs/architecture/synthesis-pipeline.md`.
- **Disposition:** The only schedule for this repository. Other files under `docs/plans/` are
  records of unfinished work. They are not a second schedule.
- **Read when:** asking what to build next, and where that work lives.
- **Search terms:** roadmap, remaining work, M11, M12, separate repository.

## Goal

Keep one schedule for this repository: what to build here, what already has a home, and what
would need a new repository.

## Architecture

Shipped behavior is in the architecture notes linked below. This file does not restate it.

## Tech Stack

This package is Python 3.13, uv, pytest, Ruff, and basedpyright.

The shipped preview is the CLI `preview` command.

The recorded browser direction is FastAPI and a React single-page application served from
one wheel. Dependencies, package name, port, and tests wait until the screen is chosen.

## Global Constraints

- A plan file stays until its code and tests show it is finished.
- Work whose code lives in another repository is scheduled there.
- A new repository starts only under the condition named for that effort.

## Renders and publishes training pairs

This repository renders synthetic OCR training pairs from recipes, then publishes them.

The shipped contracts are [Development and recipe system](../architecture/development-and-recipe-system.md),
[Synthesis pipeline](../architecture/synthesis-pipeline.md), and
[Output and publishing](../architecture/output-and-publishing.md).

Measurement and human labeling already have their own packages.
[Measurement and labeling live in other repositories](../architecture/measurement-and-labeling.md)
is the map.

## Open in this repository

Each entry is unfinished work whose code belongs here. The linked file is the record.

- `LICENSE` and `DEVELOPMENT.md` were never added.
  [Bootstrap](00-bootstrap.md)
- Corpus providers that ship are `local`, `web`, and `wikisource`. Add `web_list`,
  `hf_dataset`, `internet_archive`, or `gutenberg` only when a recipe needs that source.

  Still unresolved: `robots.txt` enforcement, non-default `max_chars` and
  `min_word_length`, and `corpus_sampling` (`uniform`, `unique_weighted`, `frequency`).
  Those sampling modes are not a runnable contract.
  [Corpus plan](03-corpus.md), [spec 04](../specs/04-corpus-providers.md)
- Text transforms still waiting on a second recipe are `u_v_swap`, `i_j_swap`, and
  `ct_st_ligature_marker`. Recipe-local inline Python is also unshipped.

  Entry points are the shipped seam. Shipped transforms do not share a general
  probability gate. `apply_lenition_dots`, `tironian_et`, and `long_s_medial` draw
  inside the transform.
  [Spec 05](../specs/05-text-transforms.md)
- Rendering still owes a font-coverage report and GSUB diagnostics. Pillow rendering,
  headings, and drop caps stay deferred.

  `glyph_runs` stay cluster geometry. M12 adds `glyph_annotations` beside them.
  [Rendering plan](05-rendering.md), [spec 06](../specs/06-rendering.md)
- Degradation stages that validation rejects are `perspective`, `scale`, `bleed_through`,
  `scratches`, `fold_line`, and `binarize`. There is no public stage plugin.
  [Degradation plan](06-degradation.md), [spec 07](../specs/07-degradation.md)
- Detection publishing is ImageFolder. Parquet sharding is not built.
  [Detection plan](09-detection-mode.md)
- Extra recipes, cloud rendering, and live statistics are separate bets, not one stretch
  milestone. [Stretch plan](10-stretch.md)
- The CLI `preview` command ships. A browser UI is a separate decision, under
  [Consider a separate repository](#consider-a-separate-repository).
- Glyph-annotation emission is not built. Nothing in `src/` writes `glyph_annotations`.
  Confirm the shared model in `pdomain-book-tools` before implementing the writer here.

  Default-on also needs a fresh decision, because it would change existing recipes and
  output digests.

  Fraktur and early-modern-English rows are later sketches, not M12 work.
  [Glyph plan](12-glyph-annotations.md), [spec 12](../specs/12-glyph-annotations-emission.md)
- Third-party plugins are undecided. Shipped seams are the corpus and transform registries.
  [Spec 09](../specs/09-extending.md)
- The dev-local upgrade guard in spec 13 is still a draft.
  [Spec 13](../specs/13-dev-local-mode-and-deps.md)
- Gaelic font URLs and license statements need a periodic check. Fonts stay unbundled.
  [Gaelic fonts](../specs/fonts-gaelic.md)
- Optional output hardening is per-sample corpus provenance, a full applied-degradation
  trace, a byte-mutation idempotency test, and a forced upload interruption.

  The manifest records configured stages. It omits which probability rolls fired and the
  sampled option values. The v1 contract does not include that trace.
  [Output and publishing](../architecture/output-and-publishing.md)

## Open in a repository that already exists

Schedule the work in the home repository. The code for these items is not in this tree.
The plan files stayed here as the design record.

| Work still open | Home | Record in this repo |
| --- | --- | --- |
| Proposal-to-region matcher | `pdomain-ocr-labeler-spa` | [Explicit membership](2026-09-08-explicit-membership-and-matching.md) |
| Word-region proposal generator, then the sibling-membership invariant: one word reachable from two sibling regions | `pdomain-book-tools` | [Explicit membership](2026-09-08-explicit-membership-and-matching.md) |
| Word ground-truth stamps and glyph-prediction retention. The labeler routes follow the book-tools change. | `pdomain-book-tools`, then `pdomain-ocr-labeler-spa` | [Word and glyph provenance](2026-09-08-word-and-glyph-provenance.md) |
| Style-span review | `pdomain-ocr-labeler-spa` | [Style-span review](2026-09-08-style-span-review-surface.md) |
| `EditorialCorrection` model | `pdomain-book-contracts` | [Editorial corrections](2026-09-08-editorial-corrections.md) |
| Labeler routes for editorial corrections. They stay behind the style-span plan. | `pdomain-ocr-labeler-spa` | [Editorial corrections](2026-09-08-editorial-corrections.md) |
| Layout-model backend. A region-export loader and an injected-model loop already exist. The loop requires a caller-supplied model. | `pdomain-ocr-training` | [Labeling track](2026-09-07-labeling-track-roadmap.md) |
| Slice 6 is held, not scheduled. Poetry is a geometry detector beside furniture (`PoetryDetector`). The slice waits for a new measured case. | `pdomain-ocr-labeler-spa` | [Labeling track](2026-09-07-labeling-track-roadmap.md) |
| Page-kind confirm returns 503 when no event store is wired. `save_page` still allows a store-less save. | `pdomain-ocr-labeler-spa` | [Page-kind storage policy](../architecture/measurement-and-labeling.md#page-kind-persistence-and-the-remaining-storage-policy) |
| Gate 3 still fails per book, at 0.9762 and 0.9429, after the small-caps rescore. The corrected pool is 0.9810 and clears 0.98. The gate is judged per book. The uncorrected pool was 0.9781. | `pdomain-pgdp-measure` | [Gate 3 recheck](../research/2026-09-07-gate3-recheck-on-the-713-page-alignment.md) |
| The 30-page book admission floor is still an uncalibrated seed. | `pdomain-pgdp-measure` | [Yield gate design](../specs/2026-08-31-pgdp-whole-book-yield-gate-design.md) and that repo's `docs/roadmap.md` |

`pdomain-pgdp-measure` keeps its own schedule in that repo's `docs/roadmap.md`.

Leave the measurement research notes under `docs/research/` here until
`pdomain-pgdp-measure` has the same numbers, because
[current state](../context/current-state.md) cites them.

The notes still hold the numbers. Their subject is `pdomain-pgdp-measure`.

## Consider a separate repository

Two efforts need a new repository when they start. Each has its own start condition.

The browser preview is a home decision, not a third effort in that pair.

**PGDP page synthesis.** Give this program a new repository when it starts. The new
repository depends on the measure package and on this renderer. Until then the program stays
deferred.

The [typography and structure design](../specs/2026-08-22-pgdp-typography-structure-synthesis-design.md)
describes a program that rectifies scanned pages, fits typography, and composites tables,
columns, poetry, and braces. The input is a measurement report. The output is a structured
page. That is a different product from a recipe renderer. `pdomain-pgdp-measure` already
keeps measurement only.

**The labeled-dataset join.** A converter with its own command line is a new repository.
It starts only after the contract exists.

This repository does not yet say what labeled export it will read.

Shared types belong in `pdomain-book-contracts`. Build that contract before any consumer
in this tree.

**Browser preview home.** Choose the screen before the package name, dependencies, port, or
tests. The CLI `preview` command stays in this repository. A browser UI is still an M11 goal
for this package.

The recorded direction is FastAPI and a React single-page application served from one wheel.
NiceGUI is withdrawn. `pyproject.toml` has no `ui` extra. No UI dependencies are selected yet.

`pdomain-ui`, `pdomain-ocr-simple-gui`, and `pdomain-ocr-trainer-spa` are alternatives if
this package should not own the screen. A new repository is for the case where none of
those homes, including this package, should own it.
[Preview UI plan](11-preview-ui.md), [scoping notes](11-preview-ui-scoping.md),
[spec 11](../specs/11-preview-ui.md)

Leave the following in their current repositories until a second consumer shows up.

- Corpus fetching. Only this package downloads recipe text.
- Degradation. Only this package dirties rendered images.
- Glyph annotation types. `pdomain-book-tools` holds the model, and the labeler reviews it.
  `pdomain-ocr-training` has a sidecar-writer decision. Emission, when built, stays here.
- Fonts with a stable URL. `pdomain-fonts` vendors only fonts that have no release URL.
  Gaelic fonts stay a user download. See [Gaelic fonts](../specs/fonts-gaelic.md).
- Layout-model weights. They stay in `pdomain-ocr-training` until a second model family exists.

## Decisions the owner still has to make

- Whether the labeler ingests PGDP corpora, or only reads measurement reports.
- The labeled-dataset contract this repository will consume.
- Whether every page mutation should refuse without an event store, or the UI should hide
  confirm. The issue is the page-kind follow-up linked above.
- What a synthesizer preview should show, now that region review lives in the labeler.
- Whether third-party plugins remain a product goal.
- Whether this tree needs a `LICENSE` file and a `DEVELOPMENT.md`.

## Records that are not this schedule

Partial specs 00, 02, 04, 05, 06, 07, and 09 still mix shipped behavior with the open items
above. Read [Synthesis pipeline](../architecture/synthesis-pipeline.md) for what the code does.
Read this file for what is left.

The PGDP draft specs from August 2026 are measurement or synthesis history.

Alignment, page templates, yield, and fragmented bands belong with `pdomain-pgdp-measure`.
That repo already has architecture notes for the commands that shipped.

The synthesis design is the separate-repository candidate above.

Implemented labeler designs from 17 and 18 September 2026 are summarized in
[Measurement and labeling](../architecture/measurement-and-labeling.md). The long specs remain
the design record until the labeler repo carries the same decisions.
