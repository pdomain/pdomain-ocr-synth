# Intent map

## Agent Index

- **Kind:** process
- **Document role:** context
- **Status:** active
- **Owner:** CT
- **Created:** 2026-07-14
- **Last verified:** 2026-11-12
- **Provenance:** authored from all 32 evidence-backed migration analyzer records, current repository
  state, the evidence-backed 2026-08-24 PGDP architecture promotion, and the 2026-09-06 promotion
  of the remaining shipped M15 slices with the retirement of their plans; the active list was
  checked again on 2026-11-06 against the plans still on disk. Region editing and partial layout training
  were checked against current sibling code on 2026-11-07. On 2026-11-12 the schedule moved to the
  roadmap, and this file kept the names older notes still cite.
- **Disposition:** Injected ground truth for active, deferred, blocked, rejected, and owner-dependent intent.

This map preserves useful unbuilt work after separating shipped truth from old
delivery scaffolding. Each item cites its source document or replacement.

## Active

The schedule is the [roadmap](../plans/README.md). It is the only open list.

Work that changes this repository next is the preview UI, once its screen is chosen, and
glyph-annotation emission after the shared model in `pdomain-book-tools` is confirmed.

## Deferred

The roadmap holds the schedule and the separate-repository judgment. This list keeps the
names that older notes and tests still cite.

- PGDP page synthesis stays deferred until it has its own repository.
  [Typography and structure design](../specs/2026-08-22-pgdp-typography-structure-synthesis-design.md)
- Bootstrap: `LICENSE` and `DEVELOPMENT.md` (`docs/plans/00-bootstrap.md`).
- Corpus: `web_list`, `hf_dataset`, `internet_archive`, `gutenberg`, `robots.txt` enforcement,
  non-default `max_chars` and `min_word_length`, and `corpus_sampling`
  (`docs/plans/03-corpus.md`, `docs/specs/04-corpus-providers.md`).
- Transforms: `u_v_swap`, `i_j_swap`, `ct_st_ligature_marker`, and recipe-local inline Python.
  Shipped transforms do not share a general probability gate (`docs/specs/05-text-transforms.md`).
- Rendering: font-coverage report, GSUB diagnostics, Pillow, headings, and drop caps
  (`docs/plans/05-rendering.md`, `docs/specs/06-rendering.md`).
- Degradation: `perspective`, `scale`, `bleed_through`, `scratches`, `fold_line`, and
  `binarize` (`docs/plans/06-degradation.md`, `docs/specs/07-degradation.md`).
- Detection publishing: parquet sharding (`docs/plans/09-detection-mode.md`).
- Output hardening: per-sample provenance, a byte-mutation test, and an interruption exercise
  ([output architecture](../architecture/output-and-publishing.md)).
- Stretch: further recipes, cloud rendering, and live statistics (`docs/plans/10-stretch.md`).
- Extensibility: recipe-local Python loaders, degradation entry-point discovery, registry schema negotiation,
  and public testing helpers remain deferred (`docs/specs/09-extending.md`). Corpus and transform entry points ship.
- Dev-local upgrade guard (`docs/specs/13-dev-local-mode-and-deps.md`).
- Gaelic font URL and license checks (`docs/specs/fonts-gaelic.md`).

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
The remaining choice is
[page-kind storage policy](../architecture/measurement-and-labeling.md#page-kind-persistence-and-the-remaining-storage-policy).

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
were complete and left the partial plans now linked through the sole roadmap; their deferred names remain above.

## Decisions retained by the 2026-11-13 retirement review

- **Needs owner decision — book-region carry policy.** The labeler carries real human rejections,
  although the original book-queue design deferred rejection carry. Ratify that behavior or choose another policy.
  Hand-drawn overlaps remain undecided; that policy also needs an explicit choice.
  The [book-queue design](../specs/2026-09-17-book-review-queue-design.md) remains partial.
- **Needs owner decision — human-review evidence.** The yield design calls for human-reviewed precision,
  but the recorded 713-page result was model-reviewed and the ledger has no reviewer-provenance field.
  The criterion is not established. Choose the required auditable evidence before claiming it passed.
  [Yield limits](../specs/2026-08-31-pgdp-whole-book-yield-gate-design.md#current-implementation-limits-2026-11-13)
  also preserve admission calibration and the missing consuming integration.
- **Deferred — detector and count limits.** The 0.7 carry threshold is uncalibrated.
  Exact word/typography freshness, untouched-page backfill, glyph prediction, kind-conditioned detectors,
  and broader item lists remain future work. These are not completed by documenting the bounded review increments.
- **Deferred — extracted alignment limits.** Calibration beyond the measured books, additional page classes,
  and rectification remain future work in the measure package. No new corpus or human precision review was run.
