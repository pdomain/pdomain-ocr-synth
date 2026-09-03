# docs/

## Agent Index

- **Kind:** usage
- **Status:** active
- **Owner:** CT
- **Created:** 2026-05-19
- **Last verified:** 2026-07-14
- **Provenance:** agent-verified from repository evidence during the 2026-07-14 docgraph migration
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

Active issues live in `docs/issues/` as governed, evidence-bearing reports. The GitHub issue
tracker is no longer used for status.
This layout is workspace-standard; see
`/workspaces/ocr-container/docs/README.md` for the master.
