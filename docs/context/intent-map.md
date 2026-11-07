# Intent map

## Agent Index

- **Kind:** context
- **Status:** active
- **Owner:** CT
- **Created:** 2026-07-14
- **Last verified:** 2026-11-06
- **Provenance:** authored from all 32 evidence-backed migration analyzer records, current repository
  state, the evidence-backed 2026-08-24 PGDP architecture promotion, and the 2026-09-06 promotion
  of the remaining shipped M15 slices with the retirement of their plans; the active list was
  checked again on 2026-11-06 against the plans still on disk
- **Disposition:** Injected ground truth for active, deferred, blocked, rejected, and owner-dependent intent.

This map preserves useful unbuilt work after separating shipped truth from old
delivery scaffolding. Each item cites its source document or replacement.

## Active

The open list is [Remaining work](../plans/README.md). The items below are the ones that still
change what this repository should do next.

- **M11 preview UI is unbuilt.** NiceGUI is not the direction. The region and glyph review work
  that M11 was being sized for now lives in the labeler, and much of it has shipped. What M11
  should show for this synthesizer is still unset
  (`docs/plans/11-preview-ui.md`, `docs/plans/11-preview-ui-scoping.md`,
  `docs/specs/11-preview-ui.md`).
- M12 glyph annotations: confirm the sibling shared model and the semantic-text
  versus presentation invariant, prototype GSUB/cluster mapping, then implement
  the Gaelic/Roman v1 model, char spans, validation, additive recognition and
  detection outputs, and disabled behavior (`docs/plans/12-glyph-annotations.md`,
  `docs/specs/12-glyph-annotations-emission.md`).
- Four labeling plans are only partly proved: explicit membership, word and glyph provenance,
  style-span review, and editorial corrections. Their files stay in `docs/plans/`.
- Slice 6 of the labeling track has no model case left, because poetry separated without one.
  Slice 7, a layout trainer, is not built
  ([labeling track roadmap](../plans/2026-09-07-labeling-track-roadmap.md)).
- Gate 3, the flat-ascender queue, the atlas policy, unused page signals, and the 30-page
  admission minimum belong to `pdomain-pgdp-measure`, not to this package. The numbers are in
  [the Gate 3 recheck](../research/2026-09-07-gate3-recheck-on-the-713-page-alignment.md).

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

These are open questions repository evidence cannot settle.

From the [split design](../specs/2026-09-06-measurement-labeling-synthesis-split-design.md):

- ~~The measurement package's name.~~ Decided on 2026-09-06: `pdomain-pgdp-measure`,
  importing as `pdomain_pgdp_measure`, with a `pgdp-measure` console script.
- ~~Whether the glyph inventory moves with the measurement library.~~ Decided on 2026-09-07: it
  moved. `pgdp-measure glyphs` is in that package. Gate 3 stays open there.
- ~~Whether this repository keeps a dependency during the transition.~~ Decided on 2026-09-07:
  one-step cutover, no dependency. See
  [Measurement and labeling](../architecture/measurement-and-labeling.md).
- ~~How region proposals persist.~~ The labeler stores confirmed regions as `Block` objects and
  stores proposals and decisions in JSONL journals, not in `extensions["labeler"]`. See the same
  architecture note.
- Whether the labeler ingests PGDP corpora directly, or only reads the measurement package's
  reports.
- The labeled-dataset contract this repository will consume. It is unspecified and is the join
  between the two halves of the suite.

Page-kind confirm returns 503 when no event store is wired, and `save_page` still allows a
store-less save. Either every mutation should refuse, or the interface should hide confirm.
The issue is
[page-kind follow-ups](../issues/2026-09-16-page-kind-follow-ups-parked-during-tasks-6-and-7.md).

For M11, the four earlier product choices are withdrawn. The package name, NiceGUI version pin,
default port, and UI test marker were all asked under a NiceGUI design that is no longer the
direction. Re-ask them only after M11's scope is chosen. The sibling SPAs differ on whether
Tailwind is used.

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
and Gaelic font reference remain active. Every analyzer record from that sweep has a
lifecycle classification. The 2026-11-06 pass retired the plans whose code and tests
were complete and left the partial plans listed under Active.
