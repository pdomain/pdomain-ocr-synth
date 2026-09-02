# Intent map

## Agent Index

- **Kind:** context
- **Status:** active
- **Owner:** CT
- **Created:** 2026-07-14
- **Last verified:** 2026-08-24
- **Provenance:** authored from all 32 evidence-backed migration analyzer records, current repository
  state, and the evidence-backed 2026-08-24 PGDP architecture promotion and plan retirement
- **Disposition:** Injected ground truth for active, deferred, blocked, rejected, and owner-dependent intent.

This map preserves useful unbuilt work after separating shipped truth from old
delivery scaffolding. Each item cites its source document or replacement.

## Active

- M15b source-line alignment is measured and passing: precision 1.0000 over 760 rows, no
  accepted declared-complex page, and all five review books admitted ([page
  classification plan](../plans/2026-08-31-pgdp-page-classification.md), [fragmented-band correction
  plan](../plans/2026-08-31-pgdp-fragmented-band-correction.md), [ocr-container-meta issue
  403](https://github.com/ConcaveTrillion/ocr-container-meta/issues/403)).
- Both previously known alignment errors are fixed. Three band-identification defects caused
  them: head-band selection picked by ordinal rather than position, a decorative rule was
  treated as a match candidate, and the speck test had to narrow at the same time because
  removing the rule alone made `379.png` worse.
- Calibrate the 30-page book admission minimum. It is an uncalibrated seed, because nothing fits
  typography from an aligned page yet and so no consumer can state its real requirement ([whole-book
  yield gate design](../specs/2026-08-31-pgdp-whole-book-yield-gate-design.md)).
- M11 preview UI: implement the localhost picker, sample grid, async rerender,
  transient overrides, manifest detail, and an explicit diff/save flow. Resolve
  the competing `pdomain_ocr_synth.ui` versus `preview` package names and decide
  whether detection preview belongs in v1 before coding
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

The migration can finish without these M11 product choices, but repository
evidence does not select them:

- Package name: confirm `pdomain_ocr_synth.ui` or retain the original design's
  `pdomain_ocr_synth.preview`. The current staged spec and scoping plan
  recommend `ui` to avoid confusion with `render.preview`, but leave final
  confirmation to the owner
  (`docs/specs/11-preview-ui.md`, `docs/plans/11-preview-ui-scoping.md`).
- NiceGUI version constraint: the optional dependency currently permits the
  repository's locked version, but the M11 compatibility policy is not stated
  in code or tests (`pyproject.toml`, `docs/plans/11-preview-ui-scoping.md`).
- Default port: no shipped console entry point, configuration, or test selects
  a port (`docs/specs/11-preview-ui.md`, `docs/plans/11-preview-ui-scoping.md`).
- UI test marker and gating: normal CI runs the full test suite, while the
  scoping plan proposes separately gated UI tests. No current workflow decides
  the marker or installation boundary (`.github/workflows/ci.yml`,
  `docs/plans/11-preview-ui-scoping.md`).

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
