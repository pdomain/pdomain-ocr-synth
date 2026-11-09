# docs/

## Agent Index

- **Kind:** usage
- **Status:** active
- **Owner:** CT
- **Created:** 2026-05-19
- **Last verified:** 2026-11-07
- **Provenance:** checked against the documentation tree and docgraph's orphan findings on 2026-11-07.
- **Disposition:** Retained as the documentation entry point.

How documentation is organized in this repo.

Repository-wide documentation governance lives in [`DOCGRAPH.md`](../DOCGRAPH.md).

| Folder | Purpose | Use when |
| --- | --- | --- |
| `architecture/` | Durable reference — how the system works today. | Capturing current shape (modules, data flow, contracts, current-state diagrams). |
| `archive/` | Cold storage. Mirrors the nine active folders. | A doc is no longer in force (shipped, superseded, abandoned). |
| `decisions/` | ADRs — dated, append-only "we chose X because Y." | Recording a specific design choice with context, alternatives, consequences. |
| `plans/` | Active execution — what order to make a spec real. | Sequencing work for an approved spec. |
| `process/` | Cross-cutting workflow conventions (verification rules, merge strategy, release process). | Capturing how the team works, not what the system does. |
| `research/` | Investigation in progress. Messy by design. | Exploring before committing to a design. |
| `runbooks/` | Operational reference — something is broken or being operated. | An on-call or ops task needs a recipe. |
| `specs/` | Aspirational, pre-implementation design. | Describing what to build, before code. |
| `templates/` | Issue, spec, plan, ADR boilerplate. | Adding a starter template for a new doc type. |
| `usage/` | Downstream reference — how to consume this app/tool/library. | A user or integrator needs to know how to use it. |

Empty folders are intentional and tracked via `.gitkeep`.

Active issues live in [the issue index](issues/README.md) as governed, evidence-bearing reports.
Cross-repository GitHub task routing is described in [CLAUDE.md](../CLAUDE.md#gh-issues).

## Current documentation

- [Current state](context/current-state.md) describes this package's scope.
- [Remaining work](plans/README.md) lists open synth and labeling work.
- [Intent map](context/intent-map.md) preserves deferred work and unresolved decisions.
- [Decisions](context/decisions.md) records why shipped plans were retired.

## Retained historical designs and plans

These records preserve earlier intent. Their placement and age do not prove that the work shipped.
Use the current-state and remaining-work indexes before treating a design as an implementation contract.

- [Fragmented-band correction design](specs/2026-08-31-pgdp-fragmented-band-correction-design.md).
- M04 text transforms is partial. Its deferred work is in [spec 05](specs/05-text-transforms.md) and the [intent map](context/intent-map.md).

## Retired session history

Session handoffs are retired and live only in Git history. The September 2026 labeling-track
handoffs are readable with `git show 2e02d92:docs/_archive/handoff/<file>`.
