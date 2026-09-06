# Roadmap — pdomain-ocr-synth implementation

## Agent Index

- **Kind:** plan
- **Status:** active
- **Owner:** CT
- **Created:** 2026-05-05
- **Last verified:** 2026-09-06
- **Provenance:** agent-verified from repository evidence, plan and architecture Agent Index
  fields, shipped code, and the measured five-book PGDP corpus runs during the 2026-09-06
  roadmap refresh
- **Disposition:** Retained as the current roadmap for both tracks.
- **Read when:** asking what shipped, what is open, or where a milestone number belongs.
- **Search terms:** roadmap, milestone, M11, M12, M14, M15, PGDP track, synth product track.

## Goal

Give the repository one milestone map. It states what shipped, what remains partial, and what is
still planned, and it routes readers to the detailed plan or architecture doc without claiming
that open work is complete.

## Architecture

The repository runs two tracks that share one codebase. Read the track frame below before reading
either table. Shipped slices move out of `docs/plans/` and into `docs/architecture/`, which is
current truth. A plan that still appears here is not yet shipped, or shipped with a gate open.

## Tech Stack

Both tracks use the repository's Python and uv toolchain, Make verification targets, pytest,
Ruff, basedpyright, pre-commit, and HarfBuzz rendering. The PGDP track adds Pillow-based scan
measurement and reads OCR geometry records produced elsewhere. It runs no model itself. The
preview UI track adds FastAPI and a React single-page application, per the workspace pattern
described under "M11 is a FastAPI and React SPA, not NiceGUI".

## Global Constraints

Each milestone must leave a runnable slice, reuse existing seams, and preserve deterministic
output and trainer compatibility. Status comes from repository evidence. Deferred UI,
annotations, extra recipes, and cloud work must stay visibly unshipped.

## Two tracks share this repository

Nothing before this refresh mapped the two numbering schemes against each other, which made the
roadmap hard to read.

**The synth product, M00 to M12.** The original goal: recipe-driven synthetic OCR training data,
first target Cló Gaelach. It invents typography from a recipe and renders it. M00 to M10 are
substantially shipped. M11 and M12 are the two open milestones, and neither has started.

**The PGDP program, M14 to M19.** Added on 2026-08-22 by the
[typography and structure synthesis design](../specs/2026-08-22-pgdp-typography-structure-synthesis-design.md).
It stops inventing typography and learns it from real scans instead: measure a book's geometry and
type from its own page images, compile that into a versioned profile, then synthesize pages from
the profile. M14 and every M15 slice have shipped. M16 to M19 have not started.

The tracks meet at M16. Until then the PGDP track only measures, and the synth product only
renders. Nothing yet composes a page from a measured profile.

There is no M13. The numbering jumps from M12 to M14 because the PGDP program was scoped as a
later continuation rather than an insertion.

## Track one: the synth product, M00 to M12

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
| [11](11-preview-ui.md) | Preview UI | not started; being re-scoped onto FastAPI + React | Visual recipe tuning in the browser | `pdomain-ocr-synth-ui` serves API and SPA from one wheel |
| [12](12-glyph-annotations.md) | Glyph-level annotations | not started | Per-word ligature / long-s / swash side channel | Synth emits `glyph_annotations.json` alongside `labels.json` |

## Track two: the PGDP program, M14 to M19

| # | Slice | Status | Delivers |
|---|-------|--------|----------|
| [14](../architecture/pgdp-ranking-and-review-queue.md) | Discovery and review queue | ✅ shipped; current architecture | `rank-pgdp` ranks projects and pages from F2 evidence |
| 15 | Scan measurement and book profiles | ✅ shipped in seven slices; see below | Measured geometry, typography, and a glyph inventory |
| 16 | Styled text and typography controls | not started | Styled spans, font families, variable axes, tracking, kerning |
| 17 | Structured-page compositor | not started | Shared page graph, then columns, tables, braces, poetry, notes |
| 18 | Local semantic inference | not started | Models for poetry, blockquotes, headings, notes, tables |
| 19 | Scan matching and evaluation | not started | Fit degradation, compare against held-out pages, measure OCR gains |

## M15 became seven slices, and all but one letter shipped

M15 was scoped as one milestone and grew lettered sub-slices as it ran. The letters appear only
inside each plan's own text, so this table is the first place they are collected.

| slice | delivers | status | current truth |
|---|---|---|---|
| M15a | `profile-pgdp`: foreground bounds, margins, ink bands, page templates, page classes | shipped | [observed geometry profiling](../architecture/pgdp-observed-geometry-profiling.md) |
| M15b | `align-pgdp`: bind F2 source lines to scan rows, `pgdp-alignment/v3` | shipped | [source-line alignment](../architecture/pgdp-source-line-alignment.md) |
| M15c | rectification and dewarping | **reserved, not started** | none; the alignment and typography plans both say not to start it |
| M15d | `typography-pgdp`: baseline, x-height, stroke, skew, word runs, all font-free | shipped | [font-free typography](../architecture/pgdp-font-free-typography.md) |
| M15e | OCR witness for continuation fragments, the `--geometry` flag | shipped | [font-free typography](../architecture/pgdp-font-free-typography.md) |
| M15f | `glyphs-pgdp`: per-book labelled glyph inventory and atlas | shipped, **Gate 3 open** | [glyph inventory](../architecture/pgdp-glyph-inventory.md) |

M15a absorbed page classification and M15b absorbed the fragmented-band correction. Both are
covered by the architecture docs above rather than by separate slice letters.

**M15f shipped with Gate 3 failing.** Label correctness on the `transcribed` tier measures 0.978
pooled against a floor of 0.98, and two of five books fail. That is the recorded result. See the
[glyph inventory architecture](../architecture/pgdp-glyph-inventory.md).

## The measurement chain runs on a stale alignment report

**Every downstream PGDP slice was measured from alignment reports that predate the three
band-identification fixes.** M15d, M15e, and M15f all ran against the `alignment-t2-*` reports,
which were written on 2026-08-31 between 17:59 and 18:18. The three fixes landed in commits
`c7c63ab` and `aa5c567` at 22:08 and 22:09 the same day, seventeen commits after the version the
reports record in their own `tool_version` field.

Those fixes raised accepted pages from 665 to 713, moved 35 pages out of `unknown`, raised
accepted-line precision from 0.9974 to 1.0000, and cut accepted pages where a dense thin band
bound a source line from four to zero. So the typography and glyph inventories are built on 665
pages of an alignment that now accepts 713, and on bindings that the fixes were written to remove.

Re-running the chain is untried and its effect is unmeasured. It is worth doing before more
geometry work, because the fixes removed exactly the wrong-ink bindings that Gate 3's failures
look like. Treat that as a hypothesis to test, not a diagnosis.

The operating note repeated in three handoffs, "use the `alignment-t2-*` reports", is now
misleading. It was written when t2 was the only report carrying the page-classification fixes,
and it stayed after later fixes made t2 stale.

## A proposed split would move measurement and labeling out of this repository

A draft design proposes separating the three jobs this repository currently does. The measurement
library would become its own package, the region and page-type vocabulary would live in
`pdomain-book-contracts`, human labeling would move to `pdomain-ocr-labeler-spa`, and this
repository would consume labeled datasets rather than produce its own measurements. Under it,
M16 through M19 stop meaning "measure more" and start meaning "consume labels".

The split is agreed in principle and its first step is planned. See the
[measurement, labeling, and synthesis split](../specs/2026-09-06-measurement-labeling-synthesis-split-design.md)
for the design, and the
[measurement library extraction plan](2026-09-06-extract-pgdp-measurement-library.md) for the
sequenced migration. Six decisions in the design are still open, including the new package's name.

The extraction's first task captures a byte-identity baseline at current `HEAD`, which also
re-runs the measurement chain on the alignment that now accepts 713 pages. That answers the stale
report question above as a side effect of making the move verifiable.

The one live PGDP plan is the
[per-book glyph inventory](2026-09-05-pgdp-per-book-glyph-inventory.md), kept open because Gate 3
fails.

## M11 is a FastAPI and React SPA, not NiceGUI

M11's earlier design chose NiceGUI and an MVVM layering by pointing at a workspace pattern:
`pd-ocr-labeler` and `pd-ocr-trainer` both used NiceGUI with the same layered shape. That
rationale has expired. Both repositories are retired, and the workspace has since moved to a
different pattern that two live repositories share.

`pdomain-ocr-labeler-spa` describes itself as a "FastAPI + React SPA replacement for
pd-ocr-labeler — single wheel that serves API + bundled SPA". `pdomain-ocr-trainer-spa`
describes itself as a "FastAPI + React SPA for OCR model training — replaces
pdomain-ocr-training NiceGUI UI". Both sit on `pdomain-ops` for shared FastAPI infrastructure and
consume the shared `@pdomain/pdomain-ui` component library.

M11 adopts that pattern. The [preview UI spec](../specs/11-preview-ui.md) carries the detail and
the re-scoping.

## Working principles for the roadmap

1. **Vertical slices.** Every milestone leaves something the user can run. No "lay the
   foundation" milestones with no demo.
2. **Dev tooling first.** M00 and M01 are weighted toward developer experience because every
   later milestone benefits.
3. **One recipe drives the synth track.** `recipes/gaelic.yaml` is the integration test through
   every milestone.
4. **Measurement drives the PGDP track.** A slice states numeric gates before it runs and records
   what they measured, passing or failing.
5. **Spec is the contract.** When in doubt the spec wins. If a milestone reveals the spec is
   wrong, update the spec before the code.
6. **No stubs in main.** A milestone is done when its surface is real, not when there is a
   placeholder. Push work in progress to a branch.
7. **Shipped work moves to architecture.** When a plan's gates pass, promote it to
   `docs/architecture/` and retire the plan. A gate that fails stays visible.

## Sequencing notes

- M00 and M01 are pure setup. No recipe execution.
- M02 unlocks `validate` and `list`, useful even before render works.
- M03 through M06 are pipeline stages. Each is testable in isolation against fixtures.
- M07 ties them together end-to-end into recognition output.
- M08 follows M07 so the publish path has real output to ship.
- M09 is gated separately because it needs bbox-aware geometric degradation.
- M11 depends on M07 only. It can land alongside M08 and M09.
- The PGDP track is strictly ordered: each slice reads the previous slice's report and refuses a
  profile that does not hash to the value the previous report recorded.
- Alignment is the bottleneck for everything downstream of it. The chain reaches five books of
  286.

## Sizing

Each milestone is sized for a focused session, not weeks. If a milestone drags past its scope,
split it or move work to a later one. These are aspirational orders of magnitude, not
commitments.

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
| 11 | re-scoping in progress; the SPA move invalidates the earlier two-session estimate |
| 12 | one to two sessions (depends on M07 + M09 + pdomain-book-tools data model) |
| 14, 15a–15f | shipped |
| 16–19 | unscoped; each needs its own plan and numeric gates before an estimate is honest |
