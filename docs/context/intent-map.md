# Intent map

## Agent Index

- **Kind:** context
- **Status:** active
- **Owner:** CT
- **Created:** 2026-07-14
- **Last verified:** 2026-09-06
- **Provenance:** authored from all 32 evidence-backed migration analyzer records, current repository
  state, the evidence-backed 2026-08-24 PGDP architecture promotion, and the 2026-09-06 promotion
  of the remaining shipped M15 slices with the retirement of their plans
- **Disposition:** Injected ground truth for active, deferred, blocked, rejected, and owner-dependent intent.

This map preserves useful unbuilt work after separating shipped truth from old
delivery scaffolding. Each item cites its source document or replacement.

## Active

- **Decide the proposed split.** A draft design would move the measurement library into its own
  package, the region and page-type vocabulary into `pdomain-book-contracts`, and human labeling
  into `pdomain-ocr-labeler-spa`, leaving this repository to consume labeled datasets. It is the
  largest open question here and every other PGDP item depends on the answer
  ([split design](../specs/2026-09-06-measurement-labeling-synthesis-split-design.md)).
- **Compare the downstream reports against the re-run chain.** The chain was re-run at `f9fdfef`
  on 2026-09-06 as Task 0 of the extraction plan, and the alignment question is settled: current
  code accepts 713 pages against the 665 the `alignment-t2-*` reports carry, a gain of 48 with 38
  of them in `projectID603d7d5e04ca0` alone. Fresh typography and glyph reports for all five books
  now exist in `/workspaces/pdomain/.extraction-baseline/`. What remains is comparing them against
  the M15d through M15f numbers, Gate 3 first, because the band-identification fixes removed the
  kind of binding its failures resemble.
- **Close Gate 3, or restate it.** Label correctness on the `transcribed` tier measures 0.978
  against a floor of 0.98, and two of five books fail. Filtering the five quality flags gives
  0.994 with every book clear. Either the gate measures the filtered inventory, or flagged glyphs
  stop being emitted, or the book is accepted at a stated lower number. The call is the owner's;
  the gate was not redefined to pass it
  ([glyph inventory](../architecture/pgdp-glyph-inventory.md)).
- **Work the flat-ascender queues.** 490 words across the five books sit unreviewed in each
  manifest's `flat_ascender_words`. `.m15f-evidence/render_flat_queue.py <book> <start> <count>`
  renders them as labelled crops.
- **Decide the atlas policy.** The corpus atlases are 7.4 MB across five books and live in the
  evidence directory rather than the repository. The glyph plan's decision 1 says atlases ship,
  and that the policy is due now that five books have landed. At the measured rate the full
  286-project corpus would reach roughly 16 million glyphs.
- **Consume the two unused page signals.** Every page records its `page_class` and its lines'
  x-height median and spread, and nothing reads them. Feeding either back into page
  classification is a slice of its own. The recorded chapter-opening figure of 43 to 67 percent
  is ambiguous between precision and recall and must be recomputed before it is relied on.
- Calibrate the 30-page book admission minimum. It is an uncalibrated seed, because nothing fits
  typography from an aligned page yet and so no consumer can state its real requirement ([whole-book
  yield gate design](../specs/2026-08-31-pgdp-whole-book-yield-gate-design.md)). Partial answer as
  of 2026-09-04: pooled x-height, baseline pitch, and stroke width settle within 0.5 px at 5 body
  pages in four books and 20 in the fifth, and word gap settles at 5, 50, 5, 30, and 5.
- **M11 preview UI is unbuilt and being re-scoped.** NiceGUI is no longer the direction. The plan
  and spec justified it by pointing at `pd-ocr-labeler` and `pd-ocr-trainer`, both retired, and
  the workspace has since moved to FastAPI with a React single-page application, shared through
  `pdomain-ops` and `@pdomain/pdomain-ui`. The scope is also unsettled: the region and glyph
  review work M11 was being sized for is moving to the labeler under the proposed split. Rewrite
  the spec and plan once the split is decided
  (`docs/plans/11-preview-ui*.md`, `docs/specs/11-preview-ui.md`).
- M12 glyph annotations: confirm the sibling shared model and the semantic-text
  versus presentation invariant, prototype GSUB/cluster mapping, then implement
  the Gaelic/Roman v1 model, char spans, validation, additive recognition and
  detection outputs, and disabled behavior (`docs/plans/12-glyph-annotations.md`,
  `docs/specs/12-glyph-annotations-emission.md`).
- Keep the roadmap index current and separate committed milestones from
  demand-driven ideas (`docs/plans/README.md`, `docs/specs/00-overview.md`).

## Deferred

- Broad PGDP synthesis program: rectify pages and fit typography; add styled typography controls;
  build a shared page graph and compositor for tables, columns, braces, and brackets; infer local
  semantics such as poetry and blockquotes; and evaluate downstream OCR and structure quality
  ([PGDP typography and structure synthesis
  design](../specs/2026-08-22-pgdp-typography-structure-synthesis-design.md)).
- Bootstrap: decide whether to add a physical `LICENSE` and whether contributor
  guidance needs `DEVELOPMENT.md` beyond current guidance
  (`docs/plans/00-bootstrap.md`).
- Corpus: add providers only for a real recipe need. Candidate work includes
  `web_list`, HF datasets, Internet Archive, Gutenberg, robots policy, honest
  local-cache reporting, `max_chars`/`min_word_length`, and clearer malformed
  Wikisource errors (`docs/plans/03-corpus.md`, `docs/specs/04-corpus-providers.md`).
- Transforms: revisit `u_v_swap`, `i_j_swap`, ligature markers, per-transform
  probability semantics, and recipe-local loading only when a second recipe
  requires them. Entry points remain the supported reusable seam
  (`docs/archive/plans/04-text-transforms.md`, `docs/specs/05-text-transforms.md`).
- Rendering: improve font-coverage UX and GSUB diagnostics; consider alternate
  corpus sampling, Pillow fallback, antialiasing/subpixel controls, headings,
  and drop caps only with demonstrated demand. Keep geometric glyph runs
  distinct from M12 semantic annotations (`docs/plans/05-rendering.md`,
  `docs/specs/06-rendering.md`).
- Degradation: preserve stage order and deterministic probability semantics.
  Before perspective or scale, define complete bbox propagation and choose
  Pillow versus OpenCV. Bleed-through, scratches, fold lines, binarization,
  texture bundling, ink-bleed bbox policy, and a public extension contract
  remain optional (`docs/plans/06-degradation.md`, `docs/specs/07-degradation.md`).
- Detection: consider parquet sharding when scale requires it, a trainer-driver
  optimization-step integration test, headings/drop caps, multi-column realism,
  and any geometry stages only with full bbox propagation
  (`docs/plans/09-detection-mode.md` and
  `docs/architecture/output-and-publishing.md`).
- Output/publishing hardening: add per-sample corpus/stage provenance, a
  byte-mutation idempotency test, and a forced interruption exercise if their
  maintenance cost is justified
  ([output architecture](../architecture/output-and-publishing.md)).
- Stretch: scope additional recipes, cloud rendering, and streaming progress as
  independent milestones instead of extending the M10 checklist
  (`docs/plans/10-stretch.md`).
- Extensibility: decide whether third-party plugins remain a product goal. If
  retained, specify degradation discovery, validation, versioning, isolation,
  and testing helpers; otherwise document only corpus and transform registries
  (`docs/specs/09-extending.md`).
- Dev-local dependency protection: revalidate the workspace contract before
  adding editable siblings, then guard `upgrade-deps` with a small tested UX
  (`docs/specs/13-dev-local-mode-and-deps.md`).
- Gaelic fonts: periodically verify external URLs and license statements while
  preserving the no-bundled-font policy (`docs/specs/fonts-gaelic.md`).

## Blocked

No repository-local item is blocked by a missing technical prerequisite. M12
must verify the sibling shared model before implementation, and M11 has bounded
design choices to settle, but both remain actionable discovery work.

## Rejected

- Do not promise every cataloged corpus provider, transform, degradation stage,
  or extension mechanism before a recipe demonstrates need.
- Do not import the trainer in ordinary output tests; use the structural
  contract because the sibling package has intrusive import-time behavior.
- Do not treat ImageFolder detection publishing as if parquet sharding shipped.
- Do not claim portable byte identity across future dependency, renderer, or
  platform versions; current determinism is scoped to the tested environment.
- Do not bundle licensed fonts or make interactive font fetching part of setup.

## Needs owner decision

These are open questions repository evidence cannot settle. The five remaining from the split
design block the largest structural decision here.

From the [split design](../specs/2026-09-06-measurement-labeling-synthesis-split-design.md):

- ~~The measurement package's name.~~ Decided on 2026-09-06: `pdomain-pgdp-measure`,
  importing as `pdomain_pgdp_measure`, with a `pgdp-measure` console script.
- Whether the glyph inventory moves with the measurement library. It is measurement, so it
  should, but its Gate 3 is open and moving a milestone with a failing gate needs a deliberate
  answer.
- Whether this repository keeps a dependency on the measurement package during the transition, or
  cuts over once.
- How region proposals persist in the labeler: as `Block` objects with `block_role_labels`, which
  already round-trips, or in the `extensions["labeler"]` slot on `PageRecord`. The labeler's
  2026-05-07 scope freeze pinned `UserPageEnvelope` v2.1 byte for byte, and region annotation is
  new persisted state, so the freeze has to be addressed rather than worked around.
- Whether the labeler ingests PGDP corpora directly, or only reads the measurement package's
  reports.
- The labeled-dataset contract this repository will consume. It is unspecified and is the join
  between the two halves of the suite.

For M11, the four earlier product choices are withdrawn. The package name, NiceGUI version pin,
default port, and UI test marker were all asked under a NiceGUI design that is no longer the
direction. Two of them no longer exist as questions. Re-ask them against the FastAPI and React
pattern once M11's scope settles, and note that the sibling SPAs differ on whether Tailwind is
used, which is the one live divergence between them.

## Legacy-unverified sweep

The 2026-08-24 PGDP migration promoted and retired the two implemented M14 ranking and M15a
observed-geometry plans.

All 32 analyzer records were classified from documents, source, tests, graph
neighbors, and commits. The implemented development, recipe-schema,
recognition-output, Hugging Face publishing plan, CLI, tutorial, output-format,
and publishing specification were promoted into current architecture and usage, tombstoned in
`docs/context/decisions.md`, and removed. Plans 00, 03-06, 09, and 10 and specs
00, 02, 04-07, and 09 remain partial. M11 is active, M12 is draft/active design,
and spec 13 remains draft. The plan index, writing standard, lint catalogue,
and Gaelic font reference remain active. Every analyzer record has a completed
lifecycle classification; the four open M11 product choices are recorded above.
