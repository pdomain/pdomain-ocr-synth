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
- [M04 text transforms](archive/plans/04-text-transforms.md) remains partial despite its archive path.

## Archived session history

These handoffs describe their sessions, not current implementation status.

- [Glyph inventory shipped](_archive/handoff/2026-09-05-051753-m15f-glyph-inventory-shipped.md).
- [Gate 3 and quality flags](_archive/handoff/2026-09-06-140411-m15f-gate3-open-and-five-quality-flags.md).
- [Measurement extraction planned](_archive/handoff/2026-09-06-214111-measurement-library-extraction-planned-and-ready.md).
- [Measurement extraction completed](_archive/handoff/2026-09-07-102549-measurement-library-extracted-and-gate-3-recheck.md).
- [Region vocabulary settled](_archive/handoff/2026-09-07-131242-labeling-track-opened-and-region-vocabulary-settled.md).
- [Four annotation plans shipped](_archive/handoff/2026-09-08-164255-annotation-track-designed-planned-and-four-plans-shipped.md).
- [Region routes shipped](_archive/handoff/2026-09-08-224245-region-routes-shipped-and-merged-task-5-waits-on-page-kind.md).
- [Page-kind stores shipped](_archive/handoff/2026-09-09-095107-page-kind-stores-shipped-across-three-repos-merge-decision-open.md).
- [Page kind unblocked](_archive/handoff/2026-09-13-174346-page-kind-unblocked-releases-cut-task-5-still-unrun.md).
- [Page kind end to end](_archive/handoff/2026-09-17-030031-page-kind-lands-end-to-end-region-routes-task-5-now-unblocked.md).
- [Geometry engine shipped](_archive/handoff/2026-09-17-102343-slice-4-ships-geometry-engine-live-gap-threshold-next.md).
- [Region pipeline on a real book](_archive/handoff/2026-09-17-122456-slice-3-ships-and-the-region-pipeline-works-on-a-real-book.md).
- [Review queue shipped](_archive/handoff/2026-09-17-153727-review-queue-ships-and-page-kind-review-is-being-built.md).
- [Slice 5 and product fixes](_archive/handoff/2026-09-18-011928-slice-5-complete-and-ten-product-honesty-bugs-closed.md).
- [Labeler decisions](_archive/handoff/2026-09-18-071345-the-labeler-backlog-is-down-to-decisions.md).
- [Slice 5 complete](_archive/handoff/2026-09-18-110548-slice-5-is-complete-and-everything-open-needs-a-decision.md).
- [Slice 6 lost its premise](_archive/handoff/2026-09-18-171724-the-labeler-shipped-v030-and-slice-6-lost-its-premise.md).
