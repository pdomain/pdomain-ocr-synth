# Current state

## Agent Index

- **Kind:** context
- **Status:** active
- **Owner:** CT
- **Created:** 2026-07-14
- **Last verified:** 2026-07-14
- **Provenance:** authored from the 2026-07-14 migration checker, analyzer records, source, tests, plans, and baseline CI
- **Disposition:** Injected operational ground truth.

M00-M10 are substantially shipped. The repository supports recipe discovery and
validation, local/web/Wikisource corpora, deterministic HarfBuzz rendering,
recognition and detection output, Hugging Face publishing, recipe linting,
audit logs, and visual regression pins. The baseline `make ci AI=1` passed before
the migration edits.

## Current architecture

[Development and recipe system](../architecture/development-and-recipe-system.md)
records the shipped development, schema, loader, validation, and CLI contracts.
[Output and publishing](../architecture/output-and-publishing.md) records local
training layouts, determinism, resume, and publishing. Recipe authors should
start with [Recipe workflow](../usage/recipe-workflow.md).

## In-flight milestones

M11 is the local preview UI. Its NiceGUI optional dependency and reusable
preview/search/validation primitives exist, but the UI package, routes,
viewmodels, save flow, and UI tests do not. M12 is glyph-annotation emission;
its shared model, recipe block, render mapping, sidecar output, and tests have
not shipped. Four non-blocking M11 product choices remain in the
[intent map](intent-map.md). The active roadmap remains
[plans/README](../plans/README.md).

## Current risks and limits

The live plans retain partial work in corpus providers, transforms, rendering,
degradation, detection, and stretch features. The strongest invariants are
deterministic seed-plus-index rendering, trainer-compatible output, snapshot-
guarded resume, and bbox propagation for geometry-changing degradation.
Current limitations and demand-driven options are classified in
[Intent map](intent-map.md); durable changed-direction decisions are in
[Decisions](decisions.md).
