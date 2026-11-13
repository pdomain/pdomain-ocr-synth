# Decisions

## Agent Index

- **Kind:** process
- **Document role:** context
- **Status:** active
- **Owner:** CT
- **Created:** 2026-07-14
- **Last verified:** 2026-11-12
- **Provenance:** authored from migration-time adversarial review, shipped code, tests, commit
  history, the evidence-backed 2026-08-24 PGDP architecture promotion and plan retirement, and
  the 2026-08-31 whole-book yield measurement over five books and 1385 pages
- **Disposition:** Append-only durable decisions and lifecycle tombstones.

## 2026-07-14: Recipes remain the persistent configuration boundary

The CLI provides operational controls and bounded overrides; it does not create
a second persistent configuration format. Pydantic models are authoritative,
the generated JSON Schema is an interoperability artifact, and runtime
validation may reject schema-cataloged features that have not shipped. This
preserves explainable snapshots and honest feature discovery. Evidence:
`src/pdomain_ocr_synth/cli.py`, `recipe/models.py`, `recipe/loader.py`,
`validation.py`, and tests for those modules.

## 2026-07-14: Current determinism is seed-and-index scoped

Workers derive randomness from the run seed and sample index, so worker-count
changes preserve current output. Resume is guarded by a matching resolved
snapshot. This does not promise byte identity across future dependency,
renderer, or platform versions. Evidence: `render/run.py`, output snapshot and
writer modules, `tests/test_cli_preview.py`, `tests/test_output_recognition.py`,
and `tests/test_output_detection.py`.

## 2026-07-14: Detection publishing uses ImageFolder

The shipped detection path stages ImageFolder data through the existing Hub
transport. The proposed parquet and 500 MB sharding design did not ship and is
deferred until scale requires it. This avoids presenting the `datasets`
dependency and parquet path as current usage. Evidence:
`publish/detection.py`, `publish/orchestrator.py`,
`tests/test_publish_detection.py`, and commit `e090040`.

## 2026-07-14: Extension claims follow shipped registries

Corpus providers and text transforms have entry-point registries. Recipe-local
Python, degradation entry-point discovery, registry schema negotiation, and a
public testing helper package are not current contracts. Documentation must not
advertise those absent mechanisms. Evidence: the two registry modules,
`degradation/pipeline.py`, `pyproject.toml`, and their tests.

## 2026-08-31: Geometry alone decides what a band is, and three tests share the job

Three assumptions in the PGDP pipeline each named a band wrongly, and all three produced the same
symptom: a source line binds to the wrong band, and every line below it shifts by one until a merged
band absorbs the surplus.

Band 0 is no longer taken for the running head. A fleck of dust can hold a band above the head, so
the classifier now picks the first band at or below `center - window` and names every ordinal down
to it as furniture. Position is the only signal available, because the profile wire format carries
band bounds and no ink, and height cannot substitute: a genuine 9px roman folio and a 5px speck are
not separable by height.

A band as tall as the type around it is never dust. `is_speck_band` required only that a band carry
under 5 percent of the page's median band ink, which condemned the section number `I.` at about
2 percent along with the dust. It now also requires the band to be at most 31 percent of the page's
median band height. Dust sits below 20 percent of that height and the wrongly dropped lines start at
42, so 31 is the midpoint of the gap rather than either of its edges.

A band that fills its box is a printed rule, not a line. `_remove_long_rules` only removes rules
spanning 80 percent of the foreground width, so a decorative rule under a chapter title survived and
took a source line. `is_rule_band` rejects a band that is under half the median band height and over
60 percent ink by area. Text rows reached 0.40 density at the 99th percentile over 17,205 matched
candidates; the measured rules ran 0.61 to 0.78.

The speck and rule changes must ship together. Removing the rule alone made `379.png` worse, because
the rule had been absorbing the line left over by the wrongly dropped `TO`; wrong matches on that
page would have risen from about 2 to about 29 while it stayed accepted.

Measured over five whole books: accepted pages rose from 665 to 713 with no book losing a page, 35
pages moved from `unknown` into a real class, and accepted pages on which a dense thin band bound a
source line fell from 4 to 0. No accepted page binds a source line to a suppressed furniture
band.

The three M15b gates were then re-measured, because the earlier ledger keys its errors by position
among a page's matches and those positions moved. A fresh stratified sample of 26 accepted pages
across the five books, 760 matched lines, was judged by rendering each matched line as an image crop
and reading it against its source line. Accepted-line precision is 1.0000 against a floor of 0.98,
no accepted page is declared complex, and all five books clear the 30-page admission minimum at 713
accepted pages. As with the 2026-08-31 measurement of 0.9716 and 0.9974, the judging was done by a
model reading rendered crops at the owner's direction, not signed off row by row by a person.

Two pages the earlier reviews had recorded as wrong are now correct. `089.png` had twelve wrong
matches of 33 while showing a matched ratio of 1.0 and a uniqueness margin of 0.275; it now matches
26 lines correctly at a margin of 1.701. The accepted-line precision gate is not re-measured here. The existing
ledger stores `incorrect_rows` as positional indices among a page's matches, and those positions
moved, so the figure of 0.9974 recorded on 2026-08-31 does not carry over and a fresh review pass is
required before the gate can be claimed again.

Versions become `first-band-templates/v3` and `source-frame-components/v4`. Neither wire shape
changed, so `pgdp-profile/v2` and `pgdp-alignment/v3` stand.

Evidence: `docs/specs/2026-08-31-pgdp-whole-book-page-templates-design.md`,
`docs/specs/2026-08-31-pgdp-fragmented-band-correction-design.md`,
`src/pdomain_ocr_synth/pgdp/page_templates.py`, `src/pdomain_ocr_synth/pgdp/alignment_image.py`,
and the five whole-book re-runs kept outside the repo.

## 2026-08-31: Book admission replaces the M15b coverage gate

A book is admitted to synthesis when it yields at least 30 accepted pages. The corpus-wide
70 percent eligible-page coverage gate is removed. Accepted-line precision at 98 percent and zero
accepted declared-complex pages remain the only corpus gates, and coverage remains a reported
per-book statistic.

Coverage was failing on the wrong population. It was measured on the bounded 25-page review set,
which M14 selects for typographic interest: against the other 1360 pages of the same five books,
that set over-represents tables 4.3 times, poetry 7.4 times, and aligned fields 5.7 times, with a
median rank score of 21.0 against 4.0.

Whole books do not rescue the fraction, and that is the point. Across five books and 1385 pages,
367 of 971 eligible pages were accepted, a corpus coverage of 0.378. The per-book counts are 226,
75, 52, 14, and 0, so three books supply enough pages to fit a style and two do not. Synthesis
consumes a book's own correctly measured pages, so the count is what decides whether a book is
usable and the fraction is incidental.

The 30-page minimum is an uncalibrated seed. Nothing fits typography from an aligned page yet, so
no consumer can state its real requirement, and corpus review is expected to set the number once
one exists.

This change was recorded before the affected numbers were re-measured, satisfying the M15b rule
against weakening a gate inside the same review run. It closes the coverage half of the follow-up
tracked as `ConcaveTrillion/ocr-container-meta#403`.

Evidence: `docs/specs/2026-08-31-pgdp-whole-book-yield-gate-design.md`,
`src/pdomain_ocr_synth/pgdp/alignment_review.py`, `tests/test_pgdp_alignment_review.py`, and the
five whole-book `pgdp-alignment/v3` runs summarized in `.m15b-evidence/wholebook-yield.json` and
`.m15b-evidence/admission-v3.json`.

### 2026-07-14 Retired: M01 development tooling plan

- Old path: `docs/archive/plans/01-dev-tooling.md`
- Outcome: implemented
- Superseded by: `docs/architecture/development-and-recipe-system.md`
- Removal commit: the unique local commit with subject
  `docs: migrate repository documentation to docgraph` (resolve with
  `git log --grep='^docs: migrate repository documentation to docgraph$'`).
- Rationale kept: shipped workflow, setup/CI boundary, schema target, and
  deviations are in the replacement architecture.
- Remaining work: dev-local upgrade protection remains deferred in `docs/context/intent-map.md`.

### 2026-07-14 Retired: M02 recipe schema plan

- Old path: `docs/archive/plans/02-recipe-schema.md`
- Outcome: implemented
- Superseded by: `docs/architecture/development-and-recipe-system.md`
- Removal commit: the unique local commit with subject
  `docs: migrate repository documentation to docgraph` (resolve with
  `git log --grep='^docs: migrate repository documentation to docgraph$'`).
- Rationale kept: PyYAML, frozen models, path resolution, schema role, and asset
  validation are in the replacement architecture.
- Remaining work: none from the completed delivery checklist.

### 2026-07-14 Retired: M07 recognition output plan

- Old path: `docs/archive/plans/07-output-recognition.md`
- Outcome: implemented
- Superseded by: `docs/architecture/output-and-publishing.md`
- Removal commit: the unique local commit with subject
  `docs: migrate repository documentation to docgraph` (resolve with
  `git log --grep='^docs: migrate repository documentation to docgraph$'`).
- Rationale kept: trainer layout, seed-plus-index determinism, guarded resume,
  and deviations are in the replacement architecture.
- Remaining work: optional per-sample provenance and stage telemetry are deferred in `docs/context/intent-map.md`.

### 2026-07-14 Retired: M08 Hugging Face publishing plan

- Old path: `docs/archive/plans/08-publishing-hf.md`
- Outcome: implemented
- Superseded by: `docs/architecture/output-and-publishing.md`
- Removal commit: the unique local commit with subject
  `docs: migrate repository documentation to docgraph` (resolve with
  `git log --grep='^docs: migrate repository documentation to docgraph$'`).
- Rationale kept: authentication order, content-hash idempotency, live-test
  boundary, and message limitation are in the replacement architecture.
- Remaining work: optional mutation and interruption hardening is deferred in `docs/context/intent-map.md`.

### 2026-07-14 Retired: CLI specification

- Old path: `docs/specs/01-cli.md`
- Outcome: implemented
- Superseded by: `docs/architecture/development-and-recipe-system.md` and `docs/usage/recipe-workflow.md`
- Removal commit: the unique local commit with subject
  `docs: migrate repository documentation to docgraph` (resolve with
  `git log --grep='^docs: migrate repository documentation to docgraph$'`).
- Rationale kept: the command/configuration boundary and supported workflow are
  in the replacements; exhaustive options come from parser help.
- Remaining work: none.

### 2026-07-14 Retired: Recipe tutorial

- Old path: `docs/specs/03-tutorial-writing-a-recipe.md`
- Outcome: superseded
- Superseded by: `docs/usage/recipe-workflow.md`
- Removal commit: the unique local commit with subject
  `docs: migrate repository documentation to docgraph` (resolve with
  `git log --grep='^docs: migrate repository documentation to docgraph$'`).
- Rationale kept: the supported scaffold, providers, transforms, validation,
  preview, render, and publish sequence is in the replacement usage guide.
- Remaining work: catalog-only providers and transforms are deferred in `docs/context/intent-map.md`.

### 2026-07-14 Retired: Output format specification

- Old path: `docs/specs/08-output-format.md`
- Outcome: implemented
- Superseded by: `docs/architecture/output-and-publishing.md`
- Removal commit: the unique local commit with subject
  `docs: migrate repository documentation to docgraph` (resolve with
  `git log --grep='^docs: migrate repository documentation to docgraph$'`).
- Rationale kept: recognition/detection layouts, trainer compatibility,
  determinism, and continuation safeguards are in the replacement architecture.
- Remaining work: M12 sidecars and stronger cross-version reproducibility remain outside v1.

### 2026-07-14 Retired: Publishing specification

- Old path: `docs/specs/10-publishing.md`
- Outcome: implemented
- Superseded by: `docs/architecture/output-and-publishing.md`
- Removal commit: the unique local commit with subject
  `docs: migrate repository documentation to docgraph` (resolve with
  `git log --grep='^docs: migrate repository documentation to docgraph$'`).
- Rationale kept: staging, auth, idempotency, tags, transport limits, and ImageFolder deviation are in the replacement architecture.
- Remaining work: parquet sharding is deferred until scale requires it.

### 2026-08-24 Retired: PGDP ranking and review queue implementation plan

- Old path: `docs/plans/2026-08-22-pgdp-ranking-review-queue.md`
- Outcome: implemented
- Superseded by: `docs/architecture/pgdp-ranking-and-review-queue.md`
- Removal commit: the unique local commit with subject
  `docs: retire implemented PGDP plans` (resolve with
  `git log --grep='^docs: retire implemented PGDP plans$'`).
- Rationale kept: shipped input, parsing, feature, scoring, selection, output, and boundary
  contracts are in the replacement architecture.
- Remaining work: the live broad PGDP design and M15 sequence remain in
  `docs/specs/2026-08-22-pgdp-typography-structure-synthesis-design.md` and
  `docs/context/intent-map.md`; none belongs to M14's completed scope.

### 2026-08-24 Retired: PGDP observed geometry profiler implementation plan

- Old path: `docs/plans/2026-08-22-pgdp-observed-geometry-profiler.md`
- Outcome: implemented
- Superseded by: `docs/architecture/pgdp-observed-geometry-profiling.md`
- Removal commit: the unique local commit with subject
  `docs: retire implemented PGDP plans` (resolve with
  `git log --grep='^docs: retire implemented PGDP plans$'`).
- Rationale kept: shipped input, source-frame measurement, exclusion, pooling, report, and boundary
  contracts are in the replacement architecture.
- Remaining work: M15b and later measurement and synthesis milestones remain in
  `docs/context/intent-map.md`; the observed-geometry slice itself has none.

### 2026-09-06 Retired: PGDP source-line alignment implementation plan

- Old path: `docs/plans/2026-08-23-pgdp-source-line-alignment.md`
- Outcome: implemented
- Superseded by: `docs/architecture/pgdp-source-line-alignment.md`
- Removal commit: the unique local commit with subject
  `docs(plans): retire the five shipped PGDP plans` (resolve with
  `git log --grep='^docs(plans): retire the five shipped PGDP plans$'`).
- Rationale kept: the shipped tokenizer, candidate extraction, dynamic-programming alignment,
  acceptance gates, and per-book admission contracts are in the replacement architecture.
- Note on status: the plan carried `status: partial` with 36 unticked task boxes at retirement.
  Those boxes are TDD checklist scaffolding, not residual scope. The code shipped and all three
  gates pass at precision 1.0000 over 760 rows.
- Remaining work: none for this slice. M15c rectification stays reserved and unstarted.

### 2026-09-06 Retired: PGDP fragmented-band correction plan

- Old path: `docs/plans/2026-08-31-pgdp-fragmented-band-correction.md`
- Outcome: implemented
- Superseded by: `docs/architecture/pgdp-source-line-alignment.md`
- Removal commit: the unique local commit with subject
  `docs(plans): retire the five shipped PGDP plans` (resolve with
  `git log --grep='^docs(plans): retire the five shipped PGDP plans$'`).
- Rationale kept: the cluster merge, minor-ink filter, and dominant-cluster candidate with its
  page-level rate limit are in the replacement architecture, together with the reason version 1
  rejected ordinary text pages over punctuation and dust.
- Remaining work: none.

### 2026-09-06 Retired: PGDP page classification plan

- Old path: `docs/plans/2026-08-31-pgdp-page-classification.md`
- Outcome: implemented
- Superseded by: `docs/architecture/pgdp-observed-geometry-profiling.md` for template fitting and
  page classes, and `docs/architecture/pgdp-source-line-alignment.md` for running-head
  suppression.
- Removal commit: the unique local commit with subject
  `docs(plans): retire the five shipped PGDP plans` (resolve with
  `git log --grep='^docs(plans): retire the five shipped PGDP plans$'`).
- Rationale kept: per-book template fitting, the four page classes, furniture suppression, and
  the two template-fitting defects that raised classified pages from 527 of 1385 to 1165 are in
  the replacement architecture.
- Remaining work: none.

### 2026-09-06 Retired: PGDP font-free typographic observables plan

- Old path: `docs/plans/2026-09-02-pgdp-font-free-typographic-observables.md`
- Outcome: implemented
- Superseded by: `docs/architecture/pgdp-font-free-typography.md`
- Removal commit: the unique local commit with subject
  `docs(plans): retire the five shipped PGDP plans` (resolve with
  `git log --grep='^docs(plans): retire the five shipped PGDP plans$'`).
- Rationale kept: the profile-hash refusal, the per-page mask reproduction check, the font-free
  per-line measurements, two-stage pooling, and the `ink-profile-word-runs/v2` word segmentation
  with its valley-depth guard are in the replacement architecture. The three research findings it
  produced stay live in `docs/research/`.
- Remaining work: none for the slice. The word-gap residual it attributed is recorded in
  `docs/research/2026-09-04-what-word-reconciliation-still-misses.md`.

### 2026-09-06 Retired: PGDP OCR witness for continuation fragments plan

- Old path: `docs/plans/2026-09-04-pgdp-ocr-witness-for-continuation-fragments.md`
- Outcome: implemented
- Superseded by: `docs/architecture/pgdp-font-free-typography.md`
- Removal commit: the unique local commit with subject
  `docs(plans): retire the five shipped PGDP plans` (resolve with
  `git log --grep='^docs(plans): retire the five shipped PGDP plans$'`).
- Rationale kept: the optional `--geometry` flag, the byte-identical behaviour without it, the
  torch-free provenance discipline, and the measured effect on reconciliation are in the
  replacement architecture.
- Remaining work: none.

### 2026-09-06 Kept live: PGDP per-book glyph inventory plan

- Path: `docs/plans/2026-09-05-pgdp-per-book-glyph-inventory.md`
- Outcome: shipped with a gate open, so not a retirement candidate
- Current truth: `docs/architecture/pgdp-glyph-inventory.md` records the shipped contract and
  states Gate 3 as failing at 0.978 pooled against a floor of 0.98.
- Why it stays: retirement policy admits only evidence-backed implemented plans. This plan holds
  live work that the architecture doc does not own: closing Gate 3, the 490 unreviewed
  flat-ascender words, and the atlas-in-repository policy that decision 1 left due.

### 2026-09-07 Moved to `pdomain-pgdp-measure`: the five PGDP architecture docs

- Old paths: `docs/architecture/pgdp-ranking-and-review-queue.md`,
  `pgdp-observed-geometry-profiling.md`, `pgdp-source-line-alignment.md`,
  `pgdp-font-free-typography.md`, `pgdp-glyph-inventory.md`
- Outcome: superseded by relocation. The docs are unchanged in substance; they now sit in
  `pdomain-pgdp-measure/docs/architecture/`, beside the code they describe.
- Superseded by: the same five files in `pdomain-pgdp-measure`
- Removal commit: the unique local commit with subject
  `docs: move the five PGDP architecture docs to pdomain-pgdp-measure` (resolve with
  `git log --grep='^docs: move the five PGDP architecture docs to pdomain-pgdp-measure$'`).
- Rationale kept: in the moved docs themselves. Their code and test paths were repointed from
  `src/pdomain_ocr_synth/pgdp/` to `src/pdomain_pgdp_measure/`, and their command names from
  `rank-pgdp` through `glyphs-pgdp` to the `pgdp-measure` subcommands. Links to research and
  decision docs that stayed here became prose naming `pdomain-ocr-synth`, following this repo's
  convention of naming a sibling repository rather than linking across repositories.
- Remaining work: none. Gate 3 stays open, and it travels with the glyph-inventory doc; see
  [the Gate 3 recheck](../research/2026-09-07-gate3-recheck-on-the-713-page-alignment.md).

The tombstones above this entry name these five docs under their old
`docs/architecture/` paths. Those references are historical and are left as written: they record
where truth lived when each plan retired.

### 2026-09-07 Moved to `pdomain-pgdp-measure`: the live glyph-inventory plan

- Old path: `docs/plans/2026-09-05-pgdp-per-book-glyph-inventory.md`
- Outcome: superseded by relocation. The plan is still live, and its Gate 3 is still open.
- Superseded by: the same file in `pdomain-pgdp-measure/docs/plans/`
- Removal commit: the unique local commit with subject
  `docs: repoint PGDP documentation at the measurement package` (resolve with
  `git log --grep='^docs: repoint PGDP documentation at the measurement package$'`).
- Rationale kept: in the moved plan. An open gate belongs with the code it gates, and that code is
  now `pdomain_pgdp_measure.glyphs`.
- Remaining work: Gate 3 is open at 0.978 against a floor of 0.98. Before deciding it, show
  `label_style` on the review sheet and rescore, because three of the 23 marked glyphs are correct
  small-caps records; see
  [the Gate 3 recheck](../research/2026-09-07-gate3-recheck-on-the-713-page-alignment.md). The 490
  flat-ascender words queued in each manifest are also unreviewed.

### 2026-11-06 Retired: measurement library extraction plan

- Old path: `docs/plans/2026-09-06-extract-pgdp-measurement-library.md`
- Outcome: implemented
- Superseded by: `docs/architecture/measurement-and-labeling.md`
- Removal commit: the unique local commit with subject
  `docs: record shipped plans as architecture and list remaining work` (resolve with
  `git log --grep='^docs: record shipped plans as architecture and list remaining work$'`).
- Rationale kept: the one-step cutover, the missing dependency, and the unchanged wire strings
  are in that architecture note. The command contracts stay in `pdomain-pgdp-measure`.
- Remaining work: none in this repository. Gate 3 stays with the measurement package.

### 2026-11-06 Retired: annotation vocabularies plan

- Old path: `docs/plans/2026-09-08-annotation-vocabularies-in-book-contracts.md`
- Outcome: implemented
- Superseded by: `docs/architecture/measurement-and-labeling.md`
- Removal commit: the unique local commit with subject
  `docs: record shipped plans as architecture and list remaining work` (resolve with
  `git log --grep='^docs: record shipped plans as architecture and list remaining work$'`).
- Rationale kept: `RegionRole` (34 values), `PageKind`, provenance enums, mappings, and
  `ReviewMetadata` source are in that note.
- Remaining work: none for this plan.

### 2026-11-06 Retired: annotation preconditions plan

- Old path: `docs/plans/2026-09-08-annotation-preconditions-in-book-tools-and-measure.md`
- Outcome: implemented
- Superseded by: `docs/architecture/measurement-and-labeling.md`
- Removal commit: the unique local commit with subject
  `docs: record shipped plans as architecture and list remaining work` (resolve with
  `git log --grep='^docs: record shipped plans as architecture and list remaining work$'`).
- Rationale kept: the duplication check, the folio mapping, the template spread, and the
  34 block roles are in that note.
- Remaining work: none for this plan.

### 2026-11-06 Retired: region stores and resolver plan

- Old path: `docs/plans/2026-09-08-region-stores-and-resolver.md`
- Outcome: implemented
- Superseded by: `docs/architecture/measurement-and-labeling.md`
- Removal commit: the unique local commit with subject
  `docs: record shipped plans as architecture and list remaining work` (resolve with
  `git log --grep='^docs: record shipped plans as architecture and list remaining work$'`).
- Rationale kept: proposal and decision journals, and `resolve_regions`, are in that note.
- Remaining work: none for this plan.

### 2026-11-06 Retired: region routes and proposal run plan

- Old path: `docs/plans/2026-09-08-region-routes-and-proposal-run.md`
- Outcome: implemented
- Superseded by: `docs/architecture/measurement-and-labeling.md`
- Removal commit: the unique local commit with subject
  `docs: record shipped plans as architecture and list remaining work` (resolve with
  `git log --grep='^docs: record shipped plans as architecture and list remaining work$'`).
- Rationale kept: the region routes, the round-trip fixture, and the two canvas layers are in
  that note.
- Remaining work: drawing, resizing, and editing word membership in the UI are still open on
  the labeling roadmap.

### 2026-11-06 Retired: page kind end to end plan

- Old path: `docs/plans/2026-09-08-page-kind-end-to-end.md`
- Outcome: implemented
- Superseded by: `docs/architecture/measurement-and-labeling.md`
- Removal commit: the unique local commit with subject
  `docs: record shipped plans as architecture and list remaining work` (resolve with
  `git log --grep='^docs: record shipped plans as architecture and list remaining work$'`).
- Rationale kept: the book-scoped proposal job, the payload fields, and the reviewed-marker
  store are in that note.
- Remaining work: whether store-less mode should stay inconsistent. See
  `docs/issues/2026-09-16-page-kind-follow-ups-parked-during-tasks-6-and-7.md`.

### 2026-11-06 Retired: geometry region proposals plan

- Old path: `docs/plans/2026-09-17-geometry-region-proposals.md`
- Outcome: implemented
- Superseded by: `docs/architecture/measurement-and-labeling.md`
- Removal commit: the unique local commit with subject
  `docs: record shipped plans as architecture and list remaining work` (resolve with
  `git log --grep='^docs: record shipped plans as architecture and list remaining work$'`).
- Rationale kept: the per-book furniture gap fit and the default composite detector are in
  that note.
- Remaining work: block boundary, blockquote, footnote, and heading proposals were never this
  plan's scope. Poetry did ship beside furniture. See the labeling roadmap.

### 2026-11-06 Retired: region review surface plan

- Old path: `docs/plans/2026-09-17-region-review-surface.md`
- Outcome: implemented
- Superseded by: `docs/architecture/measurement-and-labeling.md`
- Removal commit: the unique local commit with subject
  `docs: record shipped plans as architecture and list remaining work` (resolve with
  `git log --grep='^docs: record shipped plans as architecture and list remaining work$'`).
- Rationale kept: keyboard review, the shared mutation key, and clearing selection on page
  change are in that note.
- Remaining work: drawing a region, resizing a box, and editing word membership are still
  named on the labeling roadmap.

### 2026-11-06 Retired: furniture gap threshold issue

- Old path: `docs/issues/2026-09-17-the-furniture-gap-threshold-cannot-be-a-fixed-share.md`
- Outcome: implemented
- Superseded by: `docs/architecture/measurement-and-labeling.md`
- Removal commit: the unique local commit with subject
  `docs: record shipped plans as architecture and list remaining work` (resolve with
  `git log --grep='^docs: record shipped plans as architecture and list remaining work$'`).
- Rationale kept: the 10 percent share missed the valley, and the labeler now fits the
  threshold per book, with the fallback conditions in that note.
- Remaining work: none.

### 2026-11-06 Retired: weekly dep-refresh issue

- Old path: `docs/issues/2026-08-08-dep-refresh-cannot-auto-land.md`
- Outcome: abandoned
- Superseded by: `docs/architecture/development-and-recipe-system.md`
- Removal commit: the unique local commit with subject
  `docs: record shipped plans as architecture and list remaining work` (resolve with
  `git log --grep='^docs: record shipped plans as architecture and list remaining work$'`).
- Rationale kept: the workflow file is gone. Commit `0068970` (2026-09-13) deleted
  `.github/workflows/`, including `dep-refresh.yml`, so the dated-branch design cannot run.
- Remaining work: none. Releases are local; this note does not change that procedure.

### 2026-09-19 Operating lessons from the labeler backlog sweep

These lessons come from the 2026-09-19 handoff, retired below. They record
what worked across that sweep. They are history, not repository rules.

- **Measure before designing.** Five designs changed once measured: project
  progress, the typography numerator, word validation state, slice 6's
  premise, and the folio lookalike substitutions. The substitutions came from
  a real run's evidence rather than a guessed list.
- **Check a finding against the code before building to it.** Of 24 open
  issues in `pdomain-book-tools`, 11 were real, 3 stale and 10 not defects.
  Two of the labeler's six findings were stale the same way.
- **Ask the implementer to say when the instruction is wrong.** It happened
  eight times, and each was an improvement. One example: line merge re-sorts
  rather than appends, so no offset formula works.
- **A subagent that starts a background task and stops never gets its
  result.** Six lost time this way. Tell them to block in the foreground.
- **Do not run git in a shared checkout an agent is using.** A branch
  operation landed an agent's commit on `master`. It was recovered through the
  reflog. Use a worktree.
- **Surfaces that look like they work hide chained defects.** Each labeler
  fix exposed the next for a full day. For example, per-word sidecars did not
  follow their words through eleven structural routes, and nothing errored.

### 2026-11-09 Retired: Five releases and the labeler backlog handoff (2026-09-19)

- Old path: `docs/handoff/2026-09-19-005040-five-releases-and-the-labeler-backlog-is-empty.md`
- Outcome: superseded
- Superseded by: [intent map](intent-map.md) and the
  [labeling track roadmap](../plans/2026-09-07-labeling-track-roadmap.md)
- Removal commit: `da77cc93`
- Rationale kept: Its operating lessons are recorded in the entry above.
  Slice 6's held premise and the missing first `region-decisions.jsonl` are in
  the intent map and roadmap. The book-tools backlog items shipped in
  `ee3be65`, and `5194dfe` rejected the partial caption fix. Its parked
  labeler items are in the labeler's current state and decisions.
- Remaining work: none beyond the intent map and roadmap

### 2026-11-09 Retired: the archive folders

- Old paths: `docs/_archive/handoff/` (21 session handoffs, 2026-09-02 to 2026-09-18) and
  `docs/archive/` (the M04 text-transforms plan and empty placeholder folders)
- Outcome: deleted; retired docs live in Git history, not an archive folder
- Superseded by: [measurement and labeling](../architecture/measurement-and-labeling.md),
  [spec 05](../specs/05-text-transforms.md) and the [intent map](intent-map.md)
- Removal commit: `08854687`
- Rationale kept: Measurement and labeling now records that the region API speaks source pixels.
  pgdp-measure's architecture now records baseline overshoot and why it keeps its own F2 parser.
  Spec 05 and the intent map hold the M04 deferred transforms, and the validation error now
  points at spec 05. Read the old files with `git show 2e02d92:docs/_archive/handoff/<file>` and
  `git show 2448622:docs/archive/plans/04-text-transforms.md`.
- Remaining work: the deferred transforms in the intent map

## 2026-11-12: One roadmap, and the image pipeline is architecture

The open schedule is [the roadmap](../plans/README.md). The intent map keeps the deferred
names that older tombstones and catalog tests cite. It is not a second schedule.

Shipped corpus, transform, render, and degradation behavior is
[Synthesis pipeline](../architecture/synthesis-pipeline.md). Partial specs 04, 05, 06, and 07
stay on disk because they still hold the unbuilt names and the tests read those spec headings.

Two efforts need a new repository when they start. PGDP page synthesis gets one when that
program starts, depending on the measure package and on this renderer. A labeled-dataset
converter gets one only after shared types exist in `pdomain-book-contracts` and the join
has its own command line. The browser preview is a home decision. The CLI `preview` command
stays here. A browser UI is still an M11 goal for this package: FastAPI and a React
single-page application served from one wheel. A new UI repository is only for the case
where this package, `pdomain-ui`, `pdomain-ocr-simple-gui`, and `pdomain-ocr-trainer-spa`
should not own that screen. Matching, provenance, style spans, editorial corrections, and
the layout-model backend stay in the labeler, `pdomain-book-tools`, `pdomain-book-contracts`,
or `pdomain-ocr-training`.

Long design files were not deleted. The labeler specs are still the only full design record,
and the measurement research notes are still the citations in current state. An archive
folder was not recreated. The 2026-11-09 tombstone above records that retired docs live in
Git history.

## 2026-11-13: Reviewed architecture promotion and source retirement

Current contracts were promoted before retirement. Fresh analyzers covered all 65 indexed documents.
Actual current review records are preserved in commit `9b7e52dd10fc9c64aac87dd15c7b00ac0774b31f`; they do not
  establish a historic review.
The optional engine planner was inspected successfully, but apply was not used: its broad reference rewriting
would alter dated receipts. The direct doc-retirer procedure preserved this log and handled current links.

### 2026-11-13 Retired: Fragmented-band correction

- Old path: `docs/specs/2026-08-31-pgdp-fragmented-band-correction-design.md`
- Outcome: implemented; source document removed after promotion
- Superseded by: [current contract](../architecture/measurement-and-labeling.md#extracted-alignment-contracts)
- Removal commit: the commit containing this receipt, titled `docs: retire reviewed architecture sources`.
- Rationale kept: current architecture, inspected code/tests, and the real review record in
  `9b7e52dd10fc9c64aac87dd15c7b00ac0774b31f`.
- Remaining work: Calibration and the historical false-eligibility example remain explicit in architecture.

### 2026-11-13 Retired: Whole-book page templates

- Old path: `docs/specs/2026-08-31-pgdp-whole-book-page-templates-design.md`
- Outcome: implemented; source document removed after promotion
- Superseded by: [current contract](../architecture/measurement-and-labeling.md#extracted-alignment-contracts)
- Removal commit: the commit containing this receipt, titled `docs: retire reviewed architecture sources`.
- Rationale kept: current architecture, inspected code/tests, and the real review record in
  `9b7e52dd10fc9c64aac87dd15c7b00ac0774b31f`.
- Remaining work: Class coverage, calibration and rectification remain deferred in the measure package.

### 2026-11-13 Retired: Source-line alignment design

- Old path: `docs/specs/2026-08-23-pgdp-source-line-alignment-design.md`
- Outcome: implemented; source document removed after promotion
- Superseded by: [current contract](../architecture/measurement-and-labeling.md#extracted-alignment-contracts)
- Removal commit: the commit containing this receipt, titled `docs: retire reviewed architecture sources`.
- Rationale kept: current architecture, inspected code/tests, and the real review record in
  `9b7e52dd10fc9c64aac87dd15c7b00ac0774b31f`.
- Remaining work: The separate yield design remains live; no human precision gate or new corpus result is claimed.

### 2026-11-13 Retired: Page-kind review increment

- Old path: `docs/specs/2026-09-17-page-kind-review-design.md`
- Outcome: implemented; source document removed after promotion
- Superseded by: [current contract](../architecture/labeler-review-contracts.md#page-kind-review-and-durable-confirmation)
- Removal commit: the commit containing this receipt, titled `docs: retire reviewed architecture sources`.
- Rationale kept: current architecture, inspected code/tests, and the real review record in
  `9b7e52dd10fc9c64aac87dd15c7b00ac0774b31f`.
- Remaining work: Kind-conditioned detectors and the store-less-save policy remain open.

### 2026-11-13 Retired: Unified review queue increment

- Old path: `docs/specs/2026-09-18-one-answer-to-what-to-review-next.md`
- Outcome: implemented; source document removed after promotion
- Superseded by: [current contract](../architecture/labeler-review-contracts.md#unified-counts-have-explicit-availability-and-freshness-limits)
- Removal commit: the commit containing this receipt, titled `docs: retire reviewed architecture sources`.
- Rationale kept: current architecture, inspected code/tests, and the real review record in
  `9b7e52dd10fc9c64aac87dd15c7b00ac0774b31f`.
- Remaining work: Exact row freshness, untouched-page backfill, glyph prediction and broader item lists remain deferred.

### 2026-11-13 Retired: Geometry region proposals increment

- Old path: `docs/specs/2026-09-17-geometry-region-proposals-design.md`
- Outcome: implemented; replaced with a short retired pointer for external source references
- Superseded by: [current contract](../architecture/labeler-review-contracts.md#geometry-proposals-and-the-region-surface)
- Removal commit: the commit containing this receipt, titled `docs: retire reviewed architecture sources`.
- Rationale kept: current architecture, inspected code/tests, and the real review record in
  `9b7e52dd10fc9c64aac87dd15c7b00ac0774b31f`.
- Remaining work: Calibration, bottom furniture, braced groups and persisted measurement remain future scope.

### 2026-11-13 Retired: Region-review surface increment

- Old path: `docs/specs/2026-09-17-region-review-surface-design.md`
- Outcome: implemented; source document removed after promotion
- Superseded by: [current contract](../architecture/labeler-review-contracts.md#geometry-proposals-and-the-region-surface)
- Removal commit: the commit containing this receipt, titled `docs: retire reviewed architecture sources`.
- Rationale kept: current architecture, inspected code/tests, and the real review record in
  `9b7e52dd10fc9c64aac87dd15c7b00ac0774b31f`.
- Remaining work: General matching, sibling membership, provenance, span review and editorial corrections remain
  separate live plans.

### 2026-11-13 Retired: Five fixed page-kind defects

- Old path: `docs/issues/2026-09-16-page-kind-follow-ups-parked-during-tasks-6-and-7.md`
- Outcome: implemented; source document removed after promotion
- Superseded by: [current contract](../architecture/measurement-and-labeling.md#page-kind-persistence-and-the-remaining-storage-policy)
- Removal commit: the commit containing this receipt, titled `docs: retire reviewed architecture sources`.
- Rationale kept: current architecture, inspected code/tests, and the real review record in
  `9b7e52dd10fc9c64aac87dd15c7b00ac0774b31f`.
- Remaining work: The owner still must choose between refusing store-less saves and hiding unsupported confirmation.

### Candidates deliberately retained

The book-review-queue design remains partial because rejection carry and hand-drawn-overlap behavior need owner choices.
The yield-gate design remains live because the human-review criterion is not established and the admission seed is
  uncalibrated.
Both received actual current reviews. Neither review fabricated historical approval or claimed the product
  decisions were settled.
The intent map preserves these choices alongside the store-less-save policy. Other genuinely partial plans remain
  untouched.

### Removal commit recorded after integration

The eight 2026-11-13 retirement receipts above were committed in
`0185d795713db462f60864a1b895b31f96cae66e`. Their promotion and actual-review records preceded deletion
in `9b7e52dd10fc9c64aac87dd15c7b00ac0774b31f`. This identifies the self-referenced changeset without
rewriting any earlier receipt or decision.
