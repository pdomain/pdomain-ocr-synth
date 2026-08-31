# Decisions

## Agent Index

- **Kind:** context
- **Status:** active
- **Owner:** CT
- **Created:** 2026-07-14
- **Last verified:** 2026-08-31
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
