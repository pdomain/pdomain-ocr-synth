# Labeling track roadmap

## Agent Index

- **Kind:** plan
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-07
- **Last verified:** 2026-11-12
- **Provenance:** authored 2026-09-07 from direct inspection of `pdomain-ocr-labeler-spa`,
  `pdomain-book-contracts`, `pdomain-book-tools`, `pdomain-ocr-training`, and
  `pdomain-pgdp-measure`, plus owner direction in that session. Three premises of the
  2026-09-06 split design were falsified against the code and are corrected here. Slice 4's
  x-height spread figure recomputed 2026-09-17 and corrected here. Current UI and trainer status checked
  against labeler `5b0a624c` and training `1fb52d5` on 2026-11-07.
- **Disposition:** Active. Vocabulary, stores, routes, page kind, furniture proposals, and region review have shipped;
  see `docs/architecture/measurement-and-labeling.md`. Drawing, resizing, and membership editing also ship.
  Slice 6 remains held; slice 7 has a loader and training loop but requires a caller-supplied model.
- **Read when:** planning region labeling, the labeler's agent-facing API, the confidence review
  queue, or training a layout model for historical books.
- **Search terms:** region labeling, region proposals, label vocabulary, confidence queue, LLM
  driver, agent API, PP-DocLayout, deepdoctection, DocLayNet, layout model training, own trainer.

**Spec:** [Splitting measurement, labeling, and
synthesis](../specs/2026-09-06-measurement-labeling-synthesis-split-design.md)

This file is a record of labeling work. The schedule for this repository is the
[roadmap](README.md). The code for this track lives in `pdomain-ocr-labeler-spa`,
`pdomain-book-contracts`, `pdomain-book-tools`, and `pdomain-ocr-training`.

## Goal

Build the labeling side of the split to completion before the synthesizer consumes anything:
region proposals a machine makes, a human review surface, an API an LLM can drive, and eventually
a layout model trained on what the humans confirmed.

The owner's direction on 2026-09-07: a full human review surface **and** an LLM able to drive all
of the labeler, so a person reviews the pages a model flags at low confidence and can also spot
check the high-confidence ones. The 2026-05-07 scope freeze is lifted for this work.

## Architecture

The design makes the synthesizer a future consumer of labeled data. Measurement belongs to `pdomain-pgdp-measure`;
human review belongs to `pdomain-ocr-labeler-spa`, using shared annotation types in
`pdomain-book-contracts` and page models in `pdomain-book-tools`. The current shipped
contracts are in [Measurement and labeling](../architecture/measurement-and-labeling.md).

## Tech Stack

The labeler uses Python 3.13, FastAPI, and a React/TypeScript frontend. The shared
contracts and book-tools packages support Python 3.11 through 3.13. Slice 7 now has a Python export loader
and model-injected training loop; a complete layout-model backend remains open.

## Global Constraints

Machine proposals remain separate from human answers. The labeled-dataset contract
is still unspecified. Slice 6 stays held until a measured failure justifies a model.

The sections below preserve the September design history. In particular, the next
section's claim that no region ground truth exists was overturned on 2026-09-18;
see [the measured correction](#slice-6--model-proposed-semantics). Historical machine
specifications and branch notes describe that planning session, not this host.

## The one fact that drives the whole track

**No region ground truth exists anywhere in the suite, and no off-the-shelf vocabulary has the
words historical books need.**

The doctr corpora at `pd-ocr-trainer/ml-training/` are word boxes under a single class, `words`.
The 120-case layout regression fixture in `pdomain-book-tools/tests/fixtures/layout_regression/`
stores PP-DocLayout's own output as its expected values, so it cannot train anything.

Every candidate model shares the same gap:

| vocabulary | classes | has poetry | has blockquote | has marginalia | separates running head from folio |
| --- | ---: | --- | --- | --- | --- |
| `RegionType` (PP-DocLayout, wired today) | 14 | no | no | no | no |
| DocLayNet (deepdoctection, Docling) | 11 | no | no | no | no |
| `Block.ALLOWED_BLOCK_ROLE_LABELS` | 20 | yes | yes | no | yes |

`Block`'s list has the right words but is a loose `frozenset[str]` on a class that imports cv2, so
no repository can take the vocabulary without the imaging stack.

So the labeler is not only a review tool in this track. It is the only thing that can produce the
corpus that slices 6 and 7 need. Slices 2 through 5 are the dataset factory.

## Three premises of the split design were wrong

Checked against the code on 2026-09-07. The split design should be read with these corrections.

**The propose-and-confirm pattern is half built, not proven.** The design says the labeler
"already runs this pattern one level down, for glyph annotations." The confirm half is real: the
accept route promotes to `source="human_confirmed"` and stamps a `ProvenanceNode` into the
changelog. The propose half is not. `core/glyph/predictions.py` defines an `IGlyphPredictor`
Protocol and a `NoneGlyphPredictor` that always returns `None`, and nothing calls `.predict()`.
The frontend never calls accept-prediction either: `WordDetail.tsx` and `useWordMutations.ts` have
no reference to it. Copying the pattern means building the propose half and its UI for the first
time.

**The scope freeze does not bind region work, and the envelope it guards is retired.** D-042 in
`specs/17-decisions.md` froze six infrastructure axes: auth, S3 storage, Postgres and SQLAlchemy,
a per-user preferences backend, optimistic locking, and cloud-mode OCR. Region annotation is none
of them, and D-042 lists `UserPageEnvelope` v2.1 read/write as explicitly *in* scope. That
envelope has since been retired anyway: `persist_page_to_file` raises
`NotImplementedError("persist_page_to_file is retired — use save_page_to_store (M8b).")`.
`docs/architecture/09-persistence.md` §2 is stale. The owner lifted the freeze for this track on
2026-09-07.

**The block layer was built.** The design says `rail-target-block` and `rail-layer-block` "were
never wired" and `LineMatch.block_index` is "always `None`". Both are wired. `Rail.tsx` emits
`rail-target-block` from `TargetCell` and binds `rail-layer-block` to a real
`layerVisibility.block` toggle that `PageImageCanvas.tsx` consumes. `block_index` is derived in
`_build_line_to_block_lookup` and asserted in
`tests/unit/core/test_page_to_line_matches.py::test_line_match_carries_block_index`. There is a
block layer with a visibility toggle and a canvas consumer to hang regions on.

## Two open decisions from the split design are now answered

**Where confirmed regions persist: as `Block` objects, by owner ruling on 2026-09-07.**
Superseded by [region provenance and
persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md). This section first
recommended a sidecar map and the owner rejected it. Regions are first-class `Block` objects, and
machine proposals persist separately from them.

The objection recorded here was that the labeler never touches `Block` at all, zero import
references in the repository. That remains true and is a cost rather than a blocker. The implied
data-loss worry does not hold: `block_role_labels` is written by `Block.to_dict` and read back by
`from_dict`, so role labels round-trip. The attribute genuinely lost on that round trip is the
line-level validated flag, which is unrelated.

`extensions["labeler"]` was also rejected and stays rejected. It holds per-page session state such
as `selection_mode` and `line_filter`, not annotation payload.

**Whether the labeler ingests PGDP corpora directly: no, it reads a materialized bundle.** That
path already exists. `core/persistence/book_labeling_manifest.py` and `book_labeling_session.py`
read a sealed, content-addressed book labeling manifest for Typography Review, with canonical page
ids of the shape `pgdp:<project>:<page>`, validated in `core/typography_review.py`. It is
read-only and lazy. Region proposals should ride the same bundle rather than opening a second
ingestion path.

One caveat: `TypographyPageRecord` carries `parsed_text`, `graphemes`, `ocr_tokens`,
`style_spans`, `structural_context`, and `alignments`. It does **not** carry the line box geometry
from `pgdp-measure`'s `LineTypography`. The bundle needs extending, or a second lane, before it
can feed geometry proposals.

## The slices, in order

Slices 1 through 5 ship, including region drawing, resizing, and membership editing. Slice 6 remains held.
Slice 7 is partial: region-export loading and a training loop ship, but no default layout model is supplied. The
paragraphs below keep the original design notes, including claims that were true on 2026-09-07
and are not true now. The shipped behavior is
[Measurement and labeling](../architecture/measurement-and-labeling.md).

### Slice 1 — Region vocabulary in `pdomain-book-contracts`

**Designed and reviewed on 2026-09-07:
[region vocabulary](../specs/2026-09-07-region-vocabulary-design.md).** Thirty-four roles, the
twenty that ship today unchanged plus fourteen additions, under an additive-only rule. The vocabulary has since shipped
in `pdomain-book-contracts`.
See [Shared annotation vocabulary](../architecture/measurement-and-labeling.md#shared-annotation-vocabulary).

The role enum and a `PageKind` enum, plus mappings from PP-DocLayout's 14 `RegionType` values and
`Block`'s 20 strings so the new enum replaces them as the authority rather than becoming a third
list. The page enum is named `PageKind`, not `PageType`, because `pdomain-prep-for-pgdp` already
ships a seven-value `PageType` deciding what is written to the submission zip.

It must import without the imaging or ML stack. `tests/test_torch_free_import.py` blocks `torch`,
`doctr`, `torchvision`, `cv2`, `pandas`, `matplotlib`, and `transformers` in a clean subprocess
and asserts none reach `sys.modules`.

Served through the existing `GET /api/label-vocabulary` route, which already sources its values
from shared constants rather than re-hardcoding them, and is built once at import time.

Blocks every other slice.

### Slice 2 — Region annotations in the labeler, backend only

Confirmed regions as `Block` objects, machine proposals in their own per-run store, and a decision
record joining the two. CRUD routes plus accept and reject routes. Proposals persist rather than
being recomputed, because a model cannot be scored against decisions that were never kept. The
shape is settled in [region provenance and
persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md).

Do not copy the glyph accept-prediction route wholesale. It has no reject counterpart and never
persists the prediction, so it cannot measure its own classifier.

**Words are in scope too, by owner direction on 2026-09-07, and cost less.** `Word` already keeps
`text` with `ocr_confidence` beside `_ground_truth_text`, so the recognizer's claim survives a
human correction. What it lacks is provenance: F2 alignment, a person typing, split and merge, and
the export job all write `ground_truth_text` and nothing records which. Adding `source` to
`ReviewMetadata` closes it with no new store.

**Every region carries `source`, `confidence`, and `evidence` from its first stored byte.** This
is the one thing that cannot be retrofitted: adding it later rewrites every stored region.
At the September planning date, the confidence inventory found only three backend occurrences, all in auto-rotate.
That inventory is obsolete. Region proposals now persist confidence, furniture and poetry detectors emit it,
and the review queue can sort undecided proposals by confidence. These scores are not a claim of corpus calibration.

Drivable over HTTP the day it lands, before any UI exists.

### Slice 3 — Region review UI

**Its first increment shipped on 2026-09-17** in `pdomain-ocr-labeler-spa` `b8c2cd7`. A person can
select a region or proposal on the canvas, decide it from a panel or from the keyboard, and start the
page-kind and region proposal runs from the page actions. See
[the design](../specs/2026-09-17-region-review-surface-design.md) and
[its plan](../architecture/measurement-and-labeling.md#region-review). Not built in that increment: drawing a region,
resizing a box,
and editing word membership. Page-kind review shipped later.

A region layer on the block canvas and rail toggle that already exist. Draw, edit, accept, reject,
and a keyboard flow. Proposals must render visibly differently from confirmed regions, which is
the guard the split design names against treating model output as data.

### Slice 4 — The proposal engine, geometry first and no model

**Its first increment shipped on 2026-09-17** in `pdomain-ocr-labeler-spa` `0e35a06`. A
book-scoped run now proposes page furniture, the running head and the folio, from the ink bands the
page classifier already marks as furniture. That is the highest-volume region class in a book: 1,089
of the 1,385 pages across the five aligned corpus books carry one. See
[the geometry region proposals design](../specs/2026-09-17-geometry-region-proposals-design.md) and
[its plan](../architecture/measurement-and-labeling.md#furniture-proposals). Poetry later shipped
beside it as `PoetryDetector`. Still not covered by that increment: block boundary, blockquote,
footnote, heading, and the bottom-of-page furniture the classifier does not locate.

Turns `typography.json` plus PP-DocLayout into proposals. The signals are already measured and
consumed by nothing:

| proposal | signal |
| --- | --- |
| running head, folio | band position, already located and suppressed by `profile-pgdp` |
| block boundary | a gap in baseline pitch larger than the page's own median |
| poetry | indent, ragged right, lines short against the page's measured text width |
| blockquote | indent both sides, with leading before and after |
| footnote | x-height below the page's median |
| heading | `page_class` of `chapter_opening`, with elevated x-height spread |

`page_class` is on every page of `typography.json`, and the per-page x-height median and spread
are the `value` and `median_absolute_deviation` of that page's `x_height_px` estimate. Both are on
disk today in `/workspaces/pdomain/.extraction-baseline/projectID*/typography.json`.

**The heading row above is measured and it does not work as a gate.** The 43-to-67-percent claim
once recorded against x-height spread was a precision figure, and recomputing it gives 45 percent
pooled and 0 to 85 percent per book, at 50 percent recall. Use spread to raise confidence in a
heading proposal, never to decide one. See
[x-height spread does not find chapter openings](../research/2026-09-17-x-height-spread-does-not-find-chapter-openings.md).

This is where confidence values actually come from.

### Slice 5 — Confidence review queue and agent affordances

Spans the whole labeler, not just regions. Ranks work by confidence so a person reviews what the
model was unsure about, and can spot check what it was sure about.

**The LLM driver is a client of the same REST API, not a parallel surface.** The SPA exists
because the old labeler had no REST surface and forced clients to drive the DOM through
Playwright. The original inventory recorded 88 routes and 288 KB of generated TypeScript types;
those counts are historical. `frontend/openapi.json` is generated and ignored by Git, not committed.
A second agent-facing API would fork the existing REST contract and double the test surface.

What an agent needs beyond what the UI needs is additive and small: confidence and evidence on
every proposal, whole-page state in one call, and an endpoint answering what to look at next.

**First increment shipped 2026-09-17** in `pdomain-ocr-labeler-spa` merge `87e4a7d`, per the
[book review queue design](../specs/2026-09-17-book-review-queue-design.md). Decisions now carry
across proposal runs. `GET .../regions/review-queue` answers what to look at next for regions, in
reading or confidence order. The SPA moves between pages with work on `[` and `]`.

**Second increment shipped 2026-09-17** in `pdomain-ocr-labeler-spa` merge `2adbd46`:
[page-kind review](../specs/2026-09-17-page-kind-review-design.md), which shows each page's proposed
and confirmed kind and confirms kinds one page or many at a time.

**Third increment shipped 2026-09-17** in `pdomain-ocr-labeler-spa` merge `0536318`: a Queue drawer
tab lists the book's undecided region proposals in reading or lowest-confidence-first order, each
with the detector's evidence, and clicking one jumps to it. Still owed in this slice: words and
glyphs in the queue, and one answer to "what is next" that spans every kind of work rather than
regions alone.

**Slice 5 is complete**, 2026-09-18, with `pdomain-ocr-labeler-spa` merges `f175297`
and `0451f98`. One route answers for every kind of review work, and the SPA follows it.
Two kinds report honestly rather than counting: glyphs have no predictor, and a
typography journal past 512 KiB costs too much to read per request. The labeler's own
issue `2026-09-18-typography-numerator-needs-a-per-page-rollup.md` tracks the fix.
What remains in the track is slice 6, model-proposed semantics, and slice 7.

**The last owed increment was designed** on 2026-09-18:
[one answer to what to review next](../specs/2026-09-18-one-answer-to-what-to-review-next.md).
One route answers for every kind of work in the order the work has to happen, and one per-page
count journal makes words and typography countable at all: today counting a 300-page book's word
validation means parsing every page, about 14 seconds.

**Bottom-of-page furniture was measured and ruled out** on 2026-09-17:
[bottom furniture is too rare, and sits too close to the text](../research/2026-09-17-bottom-of-page-furniture-is-too-rare-and-too-close-to-the-text.md).
Marks appear on 6.6 percent of pages against 78.6 percent for top furniture, and they sit at
ordinary line spacing, so the gap rule that finds running heads does not transfer.

### Slice 6 — Model-proposed semantics

A vision-language model proposes role where geometry cannot separate the cases, poetry against
blockquote being the standard example. Bounded, with confidence and evidence, and never ground
truth. The synthesis design already ruled that the system "will not treat LLM output as verified
ground truth" and uses models "to bootstrap tools and labels without making them a runtime
dependency." That ruling stands.

No LLM or VLM code exists anywhere in the workspace today. This is the first.

**Slice 6 is not designed, and should not be until its premise is tested (2026-09-18).** The slice
rests on the claim that geometry cannot separate poetry from blockquote. Nobody has ever measured
that. A survey on 2026-09-18 found no per-role accuracy measurement anywhere in the workspace, and
no human correction data to mine: `region-decisions.jsonl` does not exist on this machine at all,
so not one proposal has ever been reviewed. The only region proposals that exist are page headers
and page numbers from the evidence-run null detector.

The comparable claim that *was* tested failed. X-height spread was expected to find chapter
openings and reached 45 percent precision, recorded in
[the x-height note](../research/2026-09-17-x-height-spread-does-not-find-chapter-openings.md). A
design built on an untested "geometry cannot do this" is the same bet.

So the next step in this slice is measurement, not design: run the indent, ragged-right and leading
signals this roadmap already tables over the aligned corpus and find out whether the two roles form
separable populations, how often either appears at all, and how many blocks match both. Two
outcomes change the slice. If they separate, slice 6 loses its standard example and needs a
different one. If the OCR text alone settles it, and verse lines that do not fill the measure
suggest it might, then a language model reading text may be enough and no vision model is needed.

One thing the survey settled: a model-proposed role needs no new provenance. `RegionProposal` and
`ProposalRun` already carry `model_id`, `model_version` and an open `evidence` dict, so a model is
a new run scored against the geometry it replaces, exactly as the provenance design intended.

**The premise was measured the same day, and it does not hold.**
[Ragged right finds poetry; blockquote has no geometric signature](../research/2026-09-18-ragged-right-finds-poetry-blockquote-has-no-geometric-signature.md),
over the same five aligned books as the furniture note. Three findings change this slice:

- **Poetry separates, but on the wrong signal.** Right-edge raggedness reaches 87.5 percent
  precision and 93.3 percent recall, stable across a sevenfold range of thresholds. The indent this
  roadmap named is a smear, because verse lines fall short of the measure and so look indented on
  both sides. That is exactly why the two rules as written collide on 834 blocks, 14.9 percent,
  until raggedness is added as the tiebreaker.
- **A one-line text rule beats every geometric signal.** Whether each line starts with a capital
  reaches 95.4 percent precision and 96.3 percent recall. No model of any kind is needed to find
  poetry.
- **Blockquote is the honest unknown.** The best rule found reaches 2.3 percent precision. But the
  ground truth is 44 spans across the whole corpus and heterogeneous, covering letters, stage
  directions, a chapter summary and a dateline, many with no indent at all. That is the corpus
  failing to answer, not a measured no.

So **slice 6 loses its standard example.** Poetry belongs in the geometry track beside the
furniture rules, as raggedness plus line-initial capitals. Whatever justifies a model has to be
argued from a case that survives measurement, and nobody has named one yet.

Read the caveat in the note before quoting its numbers. The pooled figures are carried almost
entirely by one book that is a poetry anthology. The other four books, the ordinary book with an
occasional stanza that this slice is actually about, hold 22 confirmed poetry blocks between them,
and per-book precision on that handful swings from 12.5 to 88.9 percent.

**The survey's "no ground truth exists" finding was wrong, and this is the more useful discovery.**
The PGDP F2 formatting round's own `/* poetry */` and `/# blockquote #/` markup is region role
ground truth, already sitting in the corpus, and it lined up with measured ink bands on 801 of
1,193 usable pages. Every future role claim can be measured against it instead of waiting for
someone to label pages by hand.

### Slice 7 — Build our own trainer, and train our own layout models

Current status, 2026-11-07: `pdomain-ocr-training` loads the labeler's `regions/labels.json`
through `load_layout_export`. `train_layout_from_config` runs training and validation batches,
emits progress, and saves a checkpoint. `LocalTrainingRunner.train_layout` exposes that path.
The caller must supply a `LayoutModel`; without one, training refuses to start. This is a partial
implementation, not evidence that a default model or a trained layout checkpoint exists.
See [the current architecture](../architecture/measurement-and-labeling.md#layout-training).

The rest of this section preserves the September design rationale.

On the corpus slices 2 through 5 produce.

**Two models, not one, by owner direction on 2026-09-08.** A book layout model proposing page kind,
and a page layout model proposing regions. They match the two scopes the provenance design
separates: page kind needs the whole book, regions need one page.

Only one of the two seams exists. The page-level detector can be swapped today through
`register_detector`. `fit_book_templates` is a fitted heuristic rather than a pluggable model, so a
book-scoped classifier has nothing to plug into and that seam must be built.

Because every proposal run records its model identity and version, replacing PP-DocLayout is a new
run rather than a migration, and the replacement can be scored against it on identical pages with
identical human answers.

**The consumption plumbing already exists and is unused.**
`pdomain_book_tools/layout/registry.py::get_detector` has a `register_detector()` extension point
documented for downstream projects and called by nobody. `PPDocLayoutPlusLDetector` accepts a
`checkpoint_path`, and `pdomain-ocr-cli` exposes `--layout-checkpoint`. Nothing in the workspace
produces such a checkpoint.

**We build our own trainer. deepdoctection is a reference implementation to study, not a
dependency to adopt.** Owner direction, 2026-09-07.

At the planning date, `pdomain-ocr-training` could not train a layout model: its `ITrainingRunner` and `IEvalRunner`
protocols hard-wire two task pairs, detection and recognition, both doctr word-level, with no
registry or plugin seam. Widening those protocols to carry a third task pair is the work, and it
is the same repository that already owns the doctr training loops, so layout training lands beside
recognition training rather than in a new home.

deepdoctection is worth reading before writing it. It is Apache-2.0, reached v1.2.7 in March 2026,
dropped TensorFlow for PyTorch at v1.0, and split into `dd-core`, `dd-datasets`, and the main
package. It is the closest worked example of a document-AI training and evaluation harness, and
its dataset package is a reasonable shape to measure our own export format against. Borrow the
structure, not the dependency.

The same repository already set the precedent for how to treat it. `10-table-structure.md` in
`pdomain-book-tools` evaluated deepdoctection for tables, rejected its Detectron2 Cascade-R-CNN
detector as an incompatible framework, chose Table Transformer instead, and decided to reimplement
deepdoctection's pure geometry as numpy with Apache-2.0 attribution, borrowing "concepts and
algorithm shape, not source." That rejection predates the v1.0 PyTorch-only rework, so the
framework objection is weaker than when written, but the borrow-concepts-not-code posture is the
one to keep. That spec is a design; no Table Transformer code ships in book-tools today.

Do not use deepdoctection's detector at runtime either. PP-DocLayout is already wired into
`pdomain-ocr-cli` and `pdomain-prep-for-pgdp`, and deepdoctection's own models carry the same
DocLayNet vocabulary gap.

Training does not fit this machine. The box has an RTX 3070 Ti Laptop with 8 GB, and
`pd-ocr-trainer/docs/plans/roadmap.md` puts real fine-tuning on rented cloud GPUs, in A10G or A100
territory, with Modal provisioning per run.

## What has shipped, and what is still owed

Checked on 2026-11-06. Shipped plans are in
[Measurement and labeling](../architecture/measurement-and-labeling.md): vocabulary, preconditions,
region stores, region routes, page kind, furniture proposals, and the region review surface.

These plans are still files because their named tests or types are missing:

- [Word and glyph provenance](2026-09-08-word-and-glyph-provenance.md)
- [Explicit membership and matching](2026-09-08-explicit-membership-and-matching.md)
- [Style span review surface](2026-09-08-style-span-review-surface.md)
- [Editorial corrections](2026-09-08-editorial-corrections.md). The plan exists. The
  `EditorialCorrection` type does not. A post-processor that would apply a correction still has
  no plan, and the plan itself says it does not apply corrections.

A ground-truth text digest beside each glyph annotation set is still part of the provenance
plan. `LigatureMark.char_span` and `long_s_positions` index into `Word.ground_truth_text`.

Slice 6's poetry example failed measurement and it remains held. Slice 7 now has a partial layout trainer;
model implementation and evaluation still need to meet the original page-level and book-level goals.

## What this roadmap does not settle

- The labeled-dataset contract the synthesizer reads at M16. It is the join between the two halves
  of the suite and still unspecified.
- Whether the book labeling manifest is extended to carry line geometry, or a second lane is
  added.
- ~~The exact region role vocabulary.~~ Shipped as 34 `RegionRole` values in
  `pdomain-book-contracts`.
- Whether the confirmed corpus is large enough to train on, which cannot be known until slices 2
  to 5 have run on real books.

## In-flight work to know about

`pdomain-ocr-labeler-spa` has an open branch `feature/edition-companion-contract`, two commits of
tests plus a dependency bump, touching the book labeling manifest. Same area as bundle loading.

## Related

- [Splitting measurement, labeling, and
  synthesis](../specs/2026-09-06-measurement-labeling-synthesis-split-design.md) — the design this
  roadmap carries out, with the three corrections above.
- [PGDP typography and page-structure synthesis
  design](../specs/2026-08-22-pgdp-typography-structure-synthesis-design.md) — the ruling that
  model output is never ground truth.
- [Measurement and labeling](../architecture/measurement-and-labeling.md) — the cutover and the
  labeling behavior that shipped.
- [Remaining work](README.md) — the short list.
