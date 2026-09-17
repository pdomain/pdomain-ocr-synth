# Labeling track roadmap

## Agent Index

- **Kind:** plan
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-07
- **Last verified:** 2026-09-17
- **Provenance:** authored 2026-09-07 from direct inspection of `pdomain-ocr-labeler-spa`,
  `pdomain-book-contracts`, `pdomain-book-tools`, `pdomain-ocr-training`, and
  `pdomain-pgdp-measure`, plus owner direction in that session. Three premises of the
  2026-09-06 split design were falsified against the code and are corrected here. Slice 4's
  x-height spread figure recomputed 2026-09-17 and corrected here.
- **Disposition:** Active. Slice 1 and slice 2 are being designed. Slices 3 to 7 are recorded
  here so they are not lost, and each needs its own design before it is built.
- **Read when:** planning region labeling, the labeler's agent-facing API, the confidence review
  queue, or training a layout model for historical books.
- **Search terms:** region labeling, region proposals, label vocabulary, confidence queue, LLM
  driver, agent API, PP-DocLayout, deepdoctection, DocLayNet, layout model training, own trainer.

**Spec:** [Splitting measurement, labeling, and
synthesis](../specs/2026-09-06-measurement-labeling-synthesis-split-design.md)

## Goal

Build the labeling side of the split to completion before the synthesizer consumes anything:
region proposals a machine makes, a human review surface, an API an LLM can drive, and eventually
a layout model trained on what the humans confirmed.

The owner's direction on 2026-09-07: a full human review surface **and** an LLM able to drive all
of the labeler, so a person reviews the pages a model flags at low confidence and can also spot
check the high-confidence ones. The 2026-05-07 scope freeze is lifted for this work.

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

Slices 1 and 2 are being designed now. The rest are recorded so they are not lost. Each needs its
own design before it is built.

### Slice 1 — Region vocabulary in `pdomain-book-contracts`

**Designed and reviewed on 2026-09-07:
[region vocabulary](../specs/2026-09-07-region-vocabulary-design.md).** Thirty-four roles, the
twenty that ship today unchanged plus fourteen additions, under an additive-only rule. Two
adversarial reviews and a recheck; no code has moved.

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
Confidence barely exists in the labeler today, three occurrences in the backend, all in
auto-rotate.

Drivable over HTTP the day it lands, before any UI exists.

### Slice 3 — Region review UI

A region layer on the block canvas and rail toggle that already exist. Draw, edit, accept, reject,
and a keyboard flow. Proposals must render visibly differently from confirmed regions, which is
the guard the split design names against treating model output as data.

### Slice 4 — The proposal engine, geometry first and no model

**Its first increment shipped on 2026-09-17** in `pdomain-ocr-labeler-spa` `0e35a06`. A
book-scoped run now proposes page furniture, the running head and the folio, from the ink bands the
page classifier already marks as furniture. That is the highest-volume region class in a book: 1,089
of the 1,385 pages across the five aligned corpus books carry one. See
[the geometry region proposals design](../specs/2026-09-17-geometry-region-proposals-design.md) and
[its plan](2026-09-17-geometry-region-proposals.md). The rows below that it does not yet cover —
block boundary, poetry, blockquote, footnote, heading, and the bottom-of-page furniture the
classifier does not locate — are the remaining increments.

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
Playwright. There are already 88 routes, a committed `frontend/openapi.json`, and 288 KB of
generated TypeScript types. A second agent-facing API would fork that contract and double the test
surface.

What an agent needs beyond what the UI needs is additive and small: confidence and evidence on
every proposal, whole-page state in one call, and an endpoint answering what to look at next.

### Slice 6 — Model-proposed semantics

A vision-language model proposes role where geometry cannot separate the cases, poetry against
blockquote being the standard example. Bounded, with confidence and evidence, and never ground
truth. The synthesis design already ruled that the system "will not treat LLM output as verified
ground truth" and uses models "to bootstrap tools and labels without making them a runtime
dependency." That ruling stands.

No LLM or VLM code exists anywhere in the workspace today. This is the first.

### Slice 7 — Build our own trainer, and train our own layout models

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

`pdomain-ocr-training` cannot train a layout model today: its `ITrainingRunner` and `IEvalRunner`
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

## What has a plan, and what is still owed

Eight plans were written on 2026-09-08 and gap-scanned twice against the design. This records what
they cover so nothing is mistaken for planned.

The first three came out of the design directly:

- [Annotation vocabularies](2026-09-08-annotation-vocabularies-in-book-contracts.md) — region
  roles, page kinds, the provenance enums, and `ReviewMetadata.source`.
- [Annotation preconditions](2026-09-08-annotation-preconditions-in-book-tools-and-measure.md) —
  the word duplication check, the page template spread, and the folio fix.
- [Region stores and resolver](2026-09-08-region-stores-and-resolver.md) — the proposal store, the
  decision store, and the one read path.

All eight gaps from the first scan now have plans, written 2026-09-08:

- [Region routes and proposal run](2026-09-08-region-routes-and-proposal-run.md) — the eight
  routes, the proposal-run job, the conformance fixture, and the browser test.
- [Word and glyph provenance](2026-09-08-word-and-glyph-provenance.md) — the writers that fill
  `ground_truth_text`, persisted glyph predictions, and the reject route.
- [Page kind end to end](2026-09-08-page-kind-end-to-end.md) — the typed field, the book-scoped
  proposal, the residual-to-confidence conversion, and the reviewed marker.
- [Explicit membership and matching](2026-09-08-explicit-membership-and-matching.md) — the
  proposal generator, the sibling-disjointness check, and the page-and-box matcher.
- [Style span review surface](2026-09-08-style-span-review-surface.md) — span identity and
  span-scoped review routes.

A second scan on 2026-09-08 read the design against all eight plans with a different lens: what the
data model cannot represent, and which flow states have no defined behavior. Six of its eight
findings were settled in the design, and two were owner rulings. Three items it opened still have
no plan:

1. **Editorial corrections.** The ink reads one way and editorial direction says another. The
   labeler records them; a post-processor applies them. They must never enter `ground_truth_text`,
   and they need their own model because a zero-width insertion is legal and `StyleSpan` forbids it.
2. **The post-processor itself.** Its input shape is settled; nothing else about it is.
3. **A ground-truth text digest beside each glyph annotation set.** `LigatureMark.char_span` and
   `long_s_positions` index into `Word.ground_truth_text`, which four writers rewrite, so the marks
   go stale silently today.

Slices 3 to 7 remain unplanned by intent: each needs its own design first.

## What this roadmap does not settle

- The labeled-dataset contract the synthesizer reads at M16. It is the join between the two halves
  of the suite and still unspecified.
- Whether the book labeling manifest is extended to carry line geometry, or a second lane is
  added.
- The exact region role vocabulary. Slice 1's design decides it.
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
- [Measurement library extraction plan](2026-09-06-extract-pgdp-measurement-library.md) — slice 2
  of the split, shipped 2026-09-07.
- [Roadmap](README.md) — both tracks.
