# Current state

## Agent Index

- **Kind:** context
- **Status:** active
- **Owner:** CT
- **Created:** 2026-07-14
- **Last verified:** 2026-08-22
- **Provenance:** authored from repository evidence, the 2026-08-22 local PGDP corpus ranking, tests, plans, and CI
- **Disposition:** Injected operational ground truth.

M00-M10 are substantially shipped. The repository supports recipe discovery and
validation, local/web/Wikisource corpora, deterministic HarfBuzz rendering,
recognition and detection output, Hugging Face publishing, recipe linting,
audit logs, and visual regression pins. The baseline `make ci AI=1` passed before
the migration edits.

M14's first runnable slice is also shipped. The local-only `rank-pgdp` command
reads PGDP project metadata and F2 text, ranks projects, and writes a bounded
JSON review queue. It does not measure typography from page images or synthesize
training data.

## PGDP ranking verification

Two runs over `/workspaces/pdomain-data/pgdp-corpus` used a project limit of 50
and a per-project page limit of 12. Both reports were byte-identical. The corpus
contained 286 projects; 285 were rankable. The report contained 1,777 stable
diagnostics and selected 600 pages across the 50 reported projects.

The top five projects were:

1. `projectID64a479f51ce5b`, *The royal mint*, score 487.
2. `projectID62930b71a45bb`, *The Kilima-Njaro expedition. [1886]*, score 479.
3. `projectID5dc798788ade0`, *The Zoology of the voyage of H.M.S. Beagle [Vol. 5 of 5]*, score 471.
4. `projectID63161caf7eafa`, *Memories of my life [1908]*, score 438.
5. `projectID657550412c8dc`, *In a German colony [1909]*, score 438.

The top project contributed 12 selected pages. In report order, their page
scores were `p092.png` 51, `p178.png` 43, `p179.png` 42, `p090.png` 39,
`p154.png` 41, `p117.png` 40, `p139.png` 39, `p150.png` 38, `p091.png` 37,
`p165.png` 37, `p121.png` 36, and `p152.png` 36. Selection balances feature
groups, so report order is not a simple descending page-score sort.

The verification commands were two identical `rank-pgdp` invocations followed
by `cmp`, focused PGDP and CLI tests, the spec-doc drift test, Markdown lint,
strict docgraph checks, and the full CI and build gates.

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

The weekly `dep-refresh` workflow has never executed since it was added
(2026-05-31), so it carries the same branch-accumulation design that already
cost peer repos stray branches, unexercised so far — see
[weekly dep-refresh shares peers' branch-accumulation design](../issues/2026-08-08-dep-refresh-cannot-auto-land.md).
