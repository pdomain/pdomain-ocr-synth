# Roadmap — pdomain-ocr-synth implementation

## Agent Index

- **Kind:** plan
- **Status:** active
- **Owner:** CT
- **Created:** 2026-05-05
- **Last verified:** 2026-08-22
- **Provenance:** agent-verified from repository evidence during the 2026-07-14 docgraph migration
  and the 2026-08-22 PGDP geometry verification.
- **Disposition:** Retained as the current roadmap, including shipped PGDP milestones.

## Goal

Provide the repository's milestone map: what shipped, what remains partial, and what is still
planned. It routes readers to detailed plans without claiming that open checklist work is complete.

## Architecture

The roadmap orders vertical slices from repository setup through corpus, rendering, output,
publishing, and the remaining UI and annotation work. Archived milestones summarize shipped slices;
linked live plans retain unresolved intent.

## Tech Stack

Milestones use the repository's Python and uv toolchain, Make verification targets, pytest, Ruff,
basedpyright, pre-commit, HarfBuzz rendering, and optional integrations named in their linked plans.

## Global Constraints

Each milestone must leave a runnable slice, reuse existing seams, and preserve deterministic output
and trainer compatibility. Status comes from repository evidence; deferred UI, annotations, extra
recipes, and cloud work must remain visibly unshipped.

This roadmap is the path to the destination described by the specs linked from
the [project README](../../README.md). Each milestone is a vertical slice that
ends in something runnable; nothing is "framework first." The order puts **dev
tooling and feedback loops early** so every later milestone benefits from them.

## Milestones

Archived plans are indexed from this roadmap when they remain useful.

| # | Milestone | Status | Goal | Outcome |
|---|-----------|--------|------|---------|
| [00](00-bootstrap.md) | Bootstrap | mostly done (LICENSE + DEVELOPMENT.md pending) | Repo exists with workspace conventions | `git clone` works; matches peer-project layout |
| 01 | Dev tooling parity | ✅ archived | Make / lint / test / pre-commit / CI | `make setup && make test && make lint` all green on a stub |
| 02 | Recipe schema + validator | ✅ archived | Recipes load, validate, list, init | `pdomain-ocr-synth validate gaelic` passes |
| [03](03-corpus.md) | Corpus providers + cache | mostly done (deferred providers noted) | Pull text from local + web + Wikisource | `pdomain-ocr-synth fetch gaelic` warms a cache |
| [04](../archive/plans/04-text-transforms.md) | Text transforms | ✅ archived | Lenition, long-s, Tironian et, base ops | Round-trip transform tests pass |
| [05](05-rendering.md) | Rendering | mostly done (deferred UX features noted) | HarfBuzz, fonts, word-crop layout | Single sample renders deterministically |
| [06](06-degradation.md) | Degradation pipeline | mostly done (deferred stages noted) | Geometric + optical + paper + jpeg stages | Sample with degradation looks plausible |
| 07 | Output: recognition mode | ✅ archived | Writer for `pdomain-ocr-training/v1` recognition | Trainer can read 50k Gaelic crops |
| 08 | HF publish | ✅ archived | Push rendered output to HF dataset repo | A dataset on HF that the trainer can consume |
| [09](09-detection-mode.md) | Output: detection mode | mostly done (future HF parquet work noted) | Layouts: paragraphs, pages; bbox-aware degradations | Trainer detection profile fed |
| [10](10-stretch.md) | Stretch | partially done (extra recipes + cloud render remain) | Extra recipes, cloud render, polish | Opt-in follow-ups |
| [11](11-preview-ui.md) | Preview UI | partial prerequisites (NiceGUI extra and backend preview primitives exist; UI unbuilt) | NiceGUI for visual recipe tuning | `pdomain-ocr-synth-preview --recipe gaelic` works |
| [12](12-glyph-annotations.md) | Glyph-level annotations | not started | Per-word ligature / long-s / swash side channel | Synth emits `glyph_annotations.json` alongside `labels.json` |
| [14](2026-08-22-pgdp-ranking-review-queue.md) | PGDP discovery and review queue | first runnable slice shipped | Rank scan projects and pages from F2 evidence | Deterministic bounded multimodal review queue |
| [15a](2026-08-22-pgdp-observed-geometry-profiler.md) | PGDP observed geometry profiler | implemented | Measure source-frame ink geometry from ranked scans | Versioned page and book observations |
| [15b](2026-08-23-pgdp-source-line-alignment.md) | PGDP source-line alignment | partial: implementation complete; corpus gate failed | Align F2 source lines with eligible single-column scan rows | Deterministic report shipped; fragmented-band extractor follow-up required |

## NiceGUI surface — preview first, explicit save

A full YAML editor reproduces VS Code at a worse quality bar. Recipes are short
and well-documented, and the YAML extension already validates against
`recipe.schema.json` (M02 deliverable). A custom editor adds maintenance with
little benefit.

A **preview UI** provides a clear benefit: pick a recipe, render N samples with
the current degradation pipeline, display them in a grid, and toggle stages or
slide probabilities to see the effect immediately. It turns "edit YAML →
re-render → open file manager" into one page. It also fits the workspace
pattern: both `pd-ocr-labeler` and `pd-ocr-trainer` use NiceGUI.

Captured as **M11** with a separate spec at
[`../specs/11-preview-ui.md`](../specs/11-preview-ui.md). The UI is
preview-first on recipes; its only feature that modifies an existing recipe is
an explicit "Diff & save" panel that shows the recipe-vs-overrides diff before
persisting. New recipe is a separate creation action.
M11 depends on M07 only — it can land alongside M08 / M09 without
ordering constraints.

## Working principles for the roadmap

1. **Vertical slices.** Every milestone leaves something the user can
   run. No "lay the foundation" milestones with no demo.
2. **Dev tooling first.** M00 + M01 are heavily weighted toward
   developer experience because every later milestone benefits.
3. **One recipe drives the work.** `recipes/gaelic.yaml` is the
   integration test through every milestone.
4. **Spec is the contract.** When in doubt, the spec wins; if a
   milestone reveals the spec is wrong, update the spec before the
   code.
5. **No stubs in main.** A milestone is done when its surface is real,
   not when there's a placeholder. Push WIP to a branch.

## Sequencing notes

- M00–M01 are pure setup; no recipe execution.
- M02 unlocks `validate` and `list`, which are nice for users tweaking
  recipes even before render works.
- M03 + M04 + M05 + M06 are pipeline stages; each one should be
  testable in isolation against fixtures.
- M07 ties them together end-to-end into recognition output.
- M08 (publish) deliberately follows M07 so the publish path has real
  output to ship.
- M09 (detection mode) is gated separately because it requires
  bbox-aware geometric degradation — different testing surface from
  recognition.

## Sizing

Each milestone is sized for a focused session, not weeks. If a
milestone is dragging past its scope, split it or move work to a
later one. The sizes below are *aspirational order of magnitude*,
not commitments.

| Milestone | Rough scope |
|-----------|-------------|
| 00 | half a session |
| 01 | one session |
| 02 | one session |
| 03 | one to two sessions |
| 04 | one session |
| 05 | two sessions |
| 06 | two sessions |
| 07 | one session |
| 08 | one session |
| 09 | two sessions |
| 10 | open-ended |
| 11 | two sessions (depends on M07; can run in parallel with M08/M09) |
| 12 | one to two sessions (depends on M07 + M09 + pdomain-book-tools data model) |

Total: ~12–15 focused sessions to a usable v0.1.0 (engine + publish);
add ~2 sessions for the preview UI.
