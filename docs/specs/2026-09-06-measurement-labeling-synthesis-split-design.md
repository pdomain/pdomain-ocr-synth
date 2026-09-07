# Splitting measurement, labeling, and synthesis across four repositories

## Agent Index

- **Kind:** spec
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-06
- **Last verified:** 2026-09-06
- **Provenance:** authored from repository evidence in `pdomain-ocr-synth`,
  `pdomain-ocr-labeler-spa`, `pdomain-book-contracts`, and `pdomain-book-tools`, read during
  the 2026-09-06 session, plus owner direction in that session
- **Disposition:** Agreed in principle on 2026-09-06. Step two is planned. The package name is
  decided; five decisions remain open.
- **Read when:** deciding where measurement, labeling, or synthesis code belongs; planning the
  measurement-library extraction; adding region or page-type annotation anywhere in the suite.
- **Search terms:** region labeling, page type, measurement library, labeled dataset, first pass,
  driver CLI, propose and confirm, cross-repo split.

This repository holds three different things, and only one of them is a synthesizer. This design
separates them, gives each an owner, and turns the synthesizer into a consumer of labeled data
rather than a producer of its own measurements.

## The problem is that one repository is doing three jobs

`pdomain-ocr-synth` currently contains:

1. **A measurement library.** `src/pdomain_ocr_synth/pgdp/` measures scan geometry, aligns PGDP F2
   text to scan rows, derives font-free typography, and cuts a glyph inventory.
2. **A review apparatus.** Throwaway scripts in `/workspaces/pdomain/.m15f-evidence/` render
   contact sheets, and verdicts live in hand-edited CSV files.
3. **A synthesizer.** The renderer, recipes, corpus providers, degradation stages, and publishing.

The synthesizer never consumes the measurement library. Nothing in
`src/pdomain_ocr_synth/` outside `pgdp/` imports it. The measurement work has produced five
measured books and no synthetic page.

Meanwhile the review apparatus badly duplicates what `pdomain-ocr-labeler-spa` already does
well. Reviewing 1,050 glyph cells for Gate 3 meant rendering PNG sheets and marking a `wrong`
column by hand. An earlier pass of that same sample scored one book at 4 wrong where a legible
pass found 12, because the sheets rendered 30 cells to a row.

## Four repositories, four jobs

| repository | owns | consumes |
|---|---|---|
| `pdomain-book-contracts` | the vocabulary: region types, page types, and their relations | nothing |
| a new measurement package | scan geometry, alignment, typography, glyph cutting | PGDP corpora |
| `pdomain-ocr-labeler-spa` | human labeling, and the machine proposals a human confirms | the measurement package |
| `pdomain-ocr-synth` | rendering synthetic pages and publishing them | labeled datasets |

The direction of the pipeline inverts. Today the synthesizer measures. Under this design the
labeler measures and labels, and the synthesizer reads what came out.

## The measurement library can move cleanly, and the numbers prove it

`src/pdomain_ocr_synth/pgdp/` is 16,018 lines across 33 modules, with 13,498 lines of tests in 37
files. Two facts make extraction cheap:

- **Its only third-party imports are Pillow, numpy, and pydantic.** No cv2, no torch, no doctr.
- **It imports nothing from the rest of `pdomain_ocr_synth`.** Not one line. The rest of the
  repository reaches it only through argument wiring in `cli.py`.

So it is already a self-contained library that happens to share a repository with a synthesizer.

It gets its own package rather than folding into `pdomain-book-tools`. It is corpus-specific,
needing PGDP project layout and F2 transcription. `pdomain-book-tools`, on the other hand, is
imported by repos that will never touch PGDP. Its own package also lets it keep its own
determinism gates on its own release cadence.

**Named `pdomain-pgdp-measure`,** confirmed by the owner on 2026-09-06, importing as
`pdomain_pgdp_measure` and exposing a `pgdp-measure` console script.

It carries its four wire contracts with it unchanged: `pgdp-profile/v2`, `pgdp-alignment/v3`,
`pgdp-typography/v1`, and `pgdp-glyphs/v1`, with their JSON Schemas.

**The extraction's acceptance test already exists.** Every one of these contracts is gated on
byte-identical output across two runs. If the five-book corpus reproduces byte for byte after the
move, the move changed nothing. That is a stronger check than a test suite passing.

## The vocabulary belongs in contracts, and today two competing versions exist

Two competing region vocabularies exist in the suite:

- `RegionType` in `pdomain_book_contracts/layout/types.py` has 14 values derived from the
  PP-DocLayout detector: text, title, section, list, table, figure, decoration, caption, header,
  footer, footnote, formula, abandoned, sidenote. It has no poetry and no blockquote.
- `Block.ALLOWED_BLOCK_ROLE_LABELS` in `pdomain_book_tools/ocr/block.py` has 20 strings including
  poetry, blockquote, page header, page footer, page number, printers mark, illustration, and
  caption. It persists through `Block.to_dict` and `from_dict`.

Neither is right on its own. The first has the wrong words. The second has the right words, but it
is a loose string set on a class that depends on cv2. A repository cannot import the valid values
without also taking on the imaging stack.

**A new enum in `pdomain-book-contracts` becomes authoritative, and maps onto
`block_role_labels` for persistence.** It covers what the
[synthesis design](2026-08-22-pgdp-typography-structure-synthesis-design.md) already enumerates:
body text, heading, running head, folio, poetry, blockquote, marginalia, footnote, table, table
cell, caption, illustration, ornament, rule, brace, and bracket.

`RegionType` stays as it is. It records what a machine detector proposed, which is a different
question from what a person meant, and merging them would erase the distinction.

A page enum joins it. **Corrected on 2026-09-07 by [region provenance and
persistence](2026-09-07-region-provenance-and-persistence-design.md).** It is named `PageKind`, not
`PageType`, because `pdomain-prep-for-pgdp` already ships a seven-value `PageType` deciding what is
written to the submission zip. And it does not carry the four classes `profile-pgdp` assigns:
`normal_recto`, `normal_verso`, `chapter_opening`, and `unknown` are `PageClass`, a measured
geometric signal that feeds a `PageKind` proposal rather than being it.

Relations get modelled explicitly rather than computed. Reading order is a free function in
`layout/regions.py` today and nothing serializes it. The `matching/` package in the same
repository already models relations as a graph, which is the precedent to follow.

Both additions satisfy the repository's hard rule: dependencies are pydantic, pydantic-core,
shapely, and regex, and a test blocks anything heavier at import time.

## The labeler proposes, and a person confirms

The labeler already runs this pattern one level down, for glyph annotations:

1. A predictor produces suggestions into `WordMatch.glyph_predictions`, tagged
   `source="predicted"`. They are never persisted and are recomputed on every page fetch.
2. The UI renders them greyed out, visibly distinct from confirmed data.
3. `POST /api/projects/{id}/pages/{index}/words/{line}/{word}/accept-prediction` promotes a
   suggestion into `glyph_annotations` with `source="human_confirmed"`, stamped into the page's
   changelog.

Region proposals copy this exactly: a region predictor, a proposal sidecar that is never ground
truth, and an accept route that promotes a confirmed region to persisted state with its source
recorded.

**One existing control must not be used.** The labeler's `PATCH` route on a paragraph takes a
`layout_type` field that looks like the right seam. Its own docstring says the value is lost on
the `Block.to_dict` to `from_dict` round trip, and it uses a bespoke six-value enum unrelated to
either vocabulary above. Anything built on it silently loses data.

**Some scaffolding is already there.** The driver contract reserves `rail-target-block` and
`rail-layer-block` test identifiers that were never wired, and `LineMatch.block_index` is defined
in the wire model and always `None`. The UI was shaped for a block layer that nobody built.

**An ingestion path already exists too.** `pdomain_book_tools.ocr.page.Page.reorganize` takes a
`PageLayout`, a list of typed boxes, and bubbles the labels onto `Block.block_role_labels`. A
first-pass proposal is a `PageLayout`, so this route exists rather than needing invention.

## Geometry proposes structure, and the measurements are already there

The first pass needs no new measurement. `LineTypography` in `pgdp/typography_models.py` already
carries, for every matched line:

- `box`, `line_ink_width_px`, and `line_ink_height_px`, giving extent and how short a line runs;
- `line_indent_px`, measured against the page class's own `text_left_px` from the book's fitted
  template rather than a raw coordinate;
- `x_height_px`, `ascender_extent_px`, `descender_extent_px`, `baseline_row_px`, and
  `stroke_width_px`;
- `words`, each with a box and the `following_gap_px` after it;
- `source_ordinal`, which joins back to the F2 transcription text.

Its own docstring says an excluded line still keeps its row because "dropping such a line would
lose the evidence a later labeler needs." This design is that later labeler.

The structural rules follow from those fields:

| proposal | signal |
|---|---|
| running head, folio | already located and suppressed by `profile-pgdp` band position |
| block boundary | a gap in baseline pitch larger than the page's own median |
| poetry | indent, ragged right, and lines short against the page's measured text width |
| blockquote | indent on both sides, with leading before and after |
| footnote | x-height below the page's median |
| heading | `page_class` of `chapter_opening`, with elevated x-height spread |

Two page signals are recorded today and consumed by nothing: each page's `page_class` and its
lines' x-height median and spread. Spread over roughly 8 px marks a mixed-size page, and the
figure recorded against it is 43 to 67 percent across the five books. This design is their first
consumer.

**That percentage needs checking before anyone builds on it.** The source sentence, in the
2026-09-06 handoff and the commit `370288b` that introduced it, can be read two ways: either 43 to
67 percent of high-spread pages are chapter openings, which would make it a precision figure, or
43 to 67 percent of chapter openings show high spread, which would make it a recall figure. The
two say different things about how usable the signal is. No evidence file in
`/workspaces/pdomain/.m15f-evidence/` records the calculation, so it has to be recomputed rather
than resolved by reading.

## The model proposes semantics, never ground truth

The [synthesis design](2026-08-22-pgdp-typography-structure-synthesis-design.md) already ruled on
this, and the ruling stands: the system "will not treat LLM output as verified ground truth," and
uses models "to bootstrap tools and labels without making them a runtime dependency."

So the division is:

- **Geometry proposes visible structure.** It is deterministic, testable, and needs no model.
- **A model proposes semantic role** where geometry is ambiguous, such as poetry against
  blockquote, reading transcription text, line geometry, and neighbouring pages.
- **Every proposal carries confidence and evidence,** and none is truth until a person confirms it.

This is the same two-tier discipline the suite already runs everywhere: `transcribed` against
`recognized` in the glyph inventory, and observed against derived, pooled, and assumed in the
profile. The first pass inherits it rather than inventing a new one.

## The driver is a CLI over HTTP, not a browser

The labeler documents a `pd-ocr-labeler-driver` agent, but it drives the UI through Playwright by
clicking elements. That is the wrong layer for this. The REST API is typed, generated into
TypeScript from OpenAPI, and covers everything except regions.

A driver needs no credentials. Local mode selects a `NoneAuth` adapter that returns the same
principal for every request, and the one hardened middleware only blocks cross-origin browser
requests. Start the server with `pdomain-ocr-labeler-ui --no-browser --port N` and issue HTTP
calls.

For tests, `build_app(settings)` with a `TestClient` drives the whole application in process, with
no socket. That is the existing pattern in `tests/conftest.py` and the driver should mirror it.

## What the synthesizer consumes

`pdomain-ocr-synth` keeps the M00 to M12 track: recipes, corpus providers, rendering, degradation,
output, and publishing. Its PGDP milestones change meaning.

M16 through M19 stop being "measure more" and become "consume labels." A labeled dataset gives the
synthesizer what it has never had: typed regions with geometry, page types, confirmed glyph
exemplars, and the reading order to compose them in.

The exact labeled-dataset contract is not specified here. It should be, before M16 starts, and it
belongs in this repository because this repository is its only consumer.

## What this design does not do

- It does not move the review apparatus's current verdicts. The Gate 3 CSV files and
  `gate3-review.json` stay where they are as a historical record.
- It does not close Gate 3. Glyph review moving into the labeler makes the review cheaper; it does
  not change the 0.978 already measured.
- It does not widen the corpus. Alignment still reaches five books of 286, and it is still the
  bottleneck everything sits behind.
- It does not specify the labeled-dataset format, the region proposal wire shape, or the labeler's
  region routes. Each needs its own design once this split is agreed.
- It does not lift the labeler's 2026-05-07 scope freeze. Region annotation is new persisted
  state, so the freeze has to be addressed deliberately, and that is the owner's call.

## Six steps carry out the split, and two of them can run at once

1. **Add the vocabulary to `pdomain-book-contracts`.** Region types, page types, and relations.
   Smallest step, no dependents yet, and both later steps need it.
2. **Extract the measurement library** into its own package, with byte-identical corpus output as
   the acceptance test. Do this before region work, so the labeler never has to depend on
   `pdomain-ocr-synth` and then be unwound.
3. **Add region proposals and confirmation to the labeler,** copying the glyph prediction pattern.
4. **Build the driver CLI,** geometry first and no model, so the structural rules are measured
   before a model is added on top.
5. **Add model-proposed semantics** for the cases geometry cannot separate.
6. **Specify the labeled-dataset contract** and point M16 at it.

Steps 1 and 2 are independent and can run together.

Step 2 is planned in detail in the
[measurement library extraction plan](../plans/2026-09-06-extract-pgdp-measurement-library.md).
Its first task captures a byte-identity baseline at current `HEAD`, which also re-runs the
measurement chain on the alignment that now accepts 713 pages rather than 665. So the stale-report
question is answered as a side effect of making the extraction verifiable.

## Open decisions

- ~~The measurement package's name.~~ **Decided 2026-09-06: `pdomain-pgdp-measure`.**
- ~~Whether the glyph inventory moves with it.~~ **Decided 2026-09-07: it moves with the rest.**
  It is measurement, and the open Gate 3 is no longer a reason to wait. Re-running the measurement
  chain on the current alignment changes nothing: all 23 glyphs the review marked wrong survive the
  band-identification fixes. The correction Gate 3 needs is to the review sheet, which hides
  `label_style` and so scores correct small-caps records as errors. Keeping the glyph modules here
  would delay the extraction without moving the gate
  ([Gate 3 recheck](../research/2026-09-07-gate3-recheck-on-the-713-page-alignment.md)).
- ~~Whether `pdomain-ocr-synth` keeps a dependency on the measurement package during the
  transition.~~ **Decided 2026-09-07: it cuts over in one step.** No dependency is added. The five
  `*-pgdp` subcommands are removed along with the modules, so `pdomain-ocr-synth` becomes a
  synthesizer only. Callers move to `pgdp-measure rank`, `profile`, `align`, `typography`, and
  `glyphs`.
- **How region proposals persist in the labeler:** as `Block` objects with `block_role_labels`,
  which already round-trips, or in the `extensions["labeler"]` namespaced slot on `PageRecord`.
- **Whether the labeler ingests PGDP corpora directly,** or only reads the measurement package's
  reports.

## Risks

**The extraction could lose determinism silently.** The byte-identity gates guard against this.
They must run against all five books before and after, not a sample.

**The labeler's scope freeze exists for a reason.** It froze `UserPageEnvelope` v2.1 byte for byte.
Region state has to go somewhere, and the `extensions` slot may be the answer that respects it.

**Two vocabularies could become three.** The new enum has to replace use of
`block_role_labels` as an authority, not sit beside it as a third list.

**A model in the loop invites treating its output as data.** The confidence and evidence fields are
the guard, and they only work if the labeler renders proposals visibly differently from confirmed
labels, the way glyph predictions already are.

## Adversarial Review

- **Stage and source:** Design-stage review during the 2026-09-06 session, from four repositories
  read directly: `pdomain-ocr-synth` source, tests, and docs; `pdomain-ocr-labeler-spa` API
  routers, domain models, adapters, architecture docs, and decisions log;
  `pdomain-book-contracts` modules and dependency rule; `pdomain-book-tools` block and page model.
- **Accepted findings:** The measurement library is genuinely decoupled, which is the fact this
  design rests on, and it was verified by import inspection rather than assumed. The labeler's
  propose-and-confirm pattern exists and is proven for glyph annotations. The `layout_type` control
  is a live trap that loses data and is documented as such in its own source.
- **Rejected alternatives:** Folding the measurement library into `pdomain-book-tools` was rejected
  because it puts corpus-specific code in a general toolkit that unrelated repositories import.
  Extending `RegionType` was rejected because it merges a detector's vocabulary with a human's.
  Building the region UI as a `pdomain-ui` stage was rejected because stages are a hard-coded export
  bundle consumed by a different family of applications, and the labeler does not use them.
- **Residual risks:** The labeled-dataset contract is unspecified and is the join between the two
  halves of the suite. The scope freeze is unresolved. The extraction is large, 16,018 lines of
  source and 13,498 of tests, and its risk is concentrated in one step.
- **Effect on this document:** Status `draft` until the owner approves the split. No code moves
  first.
