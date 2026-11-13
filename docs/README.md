# docs/

## Agent Index

- **Kind:** usage
- **Status:** active
- **Owner:** CT
- **Created:** 2026-05-19
- **Last verified:** 2026-11-12
- **Provenance:** checked against the documentation tree and docgraph's orphan findings on 2026-11-07.
  The roadmap and synthesis-pipeline note were added to this index on 2026-11-12.
- **Disposition:** Retained as the documentation entry point.

How documentation is organized in this repo.

Repository-wide documentation governance lives in [`DOCGRAPH.md`](../DOCGRAPH.md).

| Folder | Purpose | Use when |
| --- | --- | --- |
| `architecture/` | Durable reference — how the system works today. | Capturing current shape, data flow, and contracts. |
| `context/` | Current state, deferred intent, and append-only decisions. | Finding the operational summary and unresolved choices. |
| `issues/` | Evidence-bearing defects and open policy questions. | Finding active issues or their retained decisions. |
| `decisions/` | ADRs — dated, append-only "we chose X because Y." | Recording a specific design choice with context, alternatives, consequences. |
| `plans/` | Active execution — what order to make a spec real. | Sequencing work for an approved spec. |
| `process/` | Cross-cutting workflow conventions (verification rules, merge strategy, release process). | Capturing how the team works, not what the system does. |
| `research/` | Investigation in progress. Messy by design. | Exploring before committing to a design. |
| `runbooks/` | Operational reference — something is broken or being operated. | An on-call or ops task needs a recipe. |
| `specs/` | Retained design, including partial and deferred scope. | Separating implemented contracts from unfinished intent. |
| `templates/` | Issue, spec, plan, ADR boilerplate. | Adding a starter template for a new doc type. |
| `usage/` | Downstream reference — how to consume this app/tool/library. | A user or integrator needs to know how to use it. |

Retired documents live in Git history, with receipts in the decisions log. No archive tree is maintained.

Active issues live in [the issue index](issues/README.md) as governed, evidence-bearing reports.
Cross-repository GitHub task routing is described in [CLAUDE.md](../CLAUDE.md#gh-issues).

## Current documentation

- [Current state](context/current-state.md) describes this package's scope.
- [Roadmap](plans/README.md) is the only open schedule, including work that belongs in another repository.
- [Synthesis pipeline](architecture/synthesis-pipeline.md) is how a recipe becomes an image.
- [Labeler review contracts](architecture/labeler-review-contracts.md) records sibling queues and their limits.
- [Recipe runtime contracts](architecture/recipe-runtime-contracts.md) records loading, extension points, lint, and audit.
- [Intent map](context/intent-map.md) keeps deferred names that older notes cite, plus unresolved decisions.
- [Decisions](context/decisions.md) records why shipped plans were retired.

## Retained historical designs and plans

These records preserve earlier intent. Their placement and age do not prove that the work shipped.
Use the current-state and remaining-work indexes before treating a design as an implementation contract.

- [Extracted alignment contracts](architecture/measurement-and-labeling.md).
- M04 text transforms is partial. Its deferred work is in [spec 05](specs/05-text-transforms.md) and the [intent map](context/intent-map.md).

## Retired session history

Session handoffs are retired and live only in Git history. The September 2026 labeling-track
handoffs are readable with `git show 2e02d92:docs/_archive/handoff/<file>`.

The [retired geometry-design pointer](specs/2026-09-17-geometry-region-proposals-design.md)
keeps external source citations usable. Its full design lives in Git history; current behavior is in
[Labeler review contracts](architecture/labeler-review-contracts.md).
