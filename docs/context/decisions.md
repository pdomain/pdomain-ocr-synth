# Decisions

## Agent Index

- **Kind:** context
- **Status:** active
- **Owner:** CT
- **Created:** 2026-07-14
- **Last verified:** 2026-08-24
- **Provenance:** authored from migration-time adversarial review, shipped code, tests, commit
  history, and the evidence-backed 2026-08-24 PGDP architecture promotion and plan retirement
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
