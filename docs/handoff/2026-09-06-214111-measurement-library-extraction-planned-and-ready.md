---
kind: handoff
status: "active"
created: "2026-09-06"
created_at: "2026-09-06T21:41:11Z"
owner: CT
branch: master
scope: pgdp-synthesis
worktree: /workspaces/pdomain/pdomain-ocr-synth
base_commit: "fe79cc316250bd39cf86f3faf750ae50ea3ad2e7"
supersedes: "2026-09-06-140411-m15f-gate3-open-and-five-quality-flags.md"
handoff_reason: user_requested
host: claude-code
---

# The measurement library is ready to extract, and Task 0 is the gate

## Read this first

**Nothing is blocked on you, and the next action is Task 0 of the extraction plan.** It captures a
byte-identity baseline across the five books at commit `fe79cc3`, then proves that baseline is
itself reproducible before a single file moves. If determinism does not hold today, the plan stops
there by design.

This session wrote no code. It was seven documentation commits that changed what the repository
says about itself, plus one decided direction that will move most of this code to another
repository.

The plan is executable as written. No placeholders, no unresolved names, preconditions verified.

## The direction changed, and this is the part to understand

This repository does three jobs and only one of them is a synthesizer. It holds a measurement
library it never consumes, a review apparatus made of throwaway scripts, and the renderer.

The agreed split gives each an owner:

| repository | owns |
| --- | --- |
| `pdomain-book-contracts` | the region and page-type vocabulary |
| `pdomain-pgdp-measure` | scan geometry, alignment, typography, glyph cutting |
| `pdomain-ocr-labeler-spa` | human labeling and the machine proposals a person confirms |
| `pdomain-ocr-synth` | rendering synthetic pages and publishing them |

The pipeline inverts. Today the synthesizer measures. Afterwards the labeler measures and labels,
and the synthesizer reads what came out. M16 through M19 stop meaning "measure more" and start
meaning "consume labels".

The design is `docs/specs/2026-09-06-measurement-labeling-synthesis-split-design.md`, status
`active`, agreed in principle. Five decisions in it remain open.

## Why the extraction is cheap, and it was verified not assumed

`src/pdomain_ocr_synth/pgdp/` is 16,018 lines across 33 modules, with 13,498 lines of tests in 37
files. Two facts make the move a relocation rather than a refactor:

- Its only third-party imports are Pillow, numpy, and pydantic. No cv2, no torch, no doctr.
- It imports nothing from the rest of `pdomain_ocr_synth`. The whole seam is eleven lazy import
  lines inside handler functions in `cli.py`.

The acceptance test already exists. Every wire contract is gated on byte-identical output across
two runs, so if the five-book corpus reproduces byte for byte after the move, the move changed
nothing.

## Task 0 does two jobs at once

**The existing evidence directories cannot serve as the baseline.** The reports in
`/workspaces/pdomain/.m15b-evidence/`, `.m15d-evidence/`, and `.m15f-evidence/` were generated on
2026-08-31 at commit `8bc8ee10`, seventeen commits before the three band-identification fixes.
Comparing against them would compare two changes at once.

So Task 0 re-runs the whole chain at current `HEAD`. That is also the answer to a question this
repository has been carrying unknowingly, described next.

## The measurement chain has been running on a stale alignment

M15d, M15e, and M15f all read the `alignment-t2-*` reports, written on 2026-08-31 between 17:59
and 18:18. The three band-identification fixes landed in commits `c7c63ab` and `aa5c567` at 22:08
and 22:09 the same day.

Those fixes raised accepted pages from 665 to 713, moved 35 pages out of `unknown`, raised
accepted-line precision from 0.9974 to 1.0000, and cut accepted pages where a dense thin band
bound a source line from four to zero.

So the typography and glyph inventories are built on 665 pages of an alignment that now accepts
713, and on bindings the fixes were written to remove. **This is worth testing against Gate 3**,
because the fixes removed exactly the kind of wrong-ink binding Gate 3's failures resemble. Treat
that as a hypothesis, not a diagnosis.

The note repeated in three handoffs, "use the `alignment-t2-*` reports", is now misleading. It was
written when t2 was the only report carrying the page-classification fixes.

## What shipped this session

Seven commits, each through `make ci AI=1` and `docgraph check --strict`:

| commit | what |
| --- | --- |
| `28876c2` | three architecture docs promoted, profiling doc brought to `pgdp-profile/v2`, roadmap rewritten around two tracks |
| `907f776` | five shipped plans retired with tombstones, references repointed, three handoffs archived |
| `52b1e0e` | the split design |
| `45cb573` | context docs refreshed, `nicegui` extra removed |
| `a55effb` | the extraction plan |
| `65209b0` | the package name settled |
| `fe79cc3` | per-book geometry path fix in the plan |

**M15f's plan stays live** because Gate 3 fails at 0.978. Retirement policy admits only
evidence-backed implemented plans, and that plan still holds work the architecture doc does not
own.

## Preconditions, verified on 2026-09-06

- `/workspaces/pdomain-data/pgdp-corpus` is mounted, 324 projects, all five aligned books present.
- OCR witness records exist per book at
  `/workspaces/pdomain-data/typography/geometry-v1/<BOOK>.jsonl`.
- Working tree is clean at `fe79cc3`.

## Two traps recorded, so nobody finds them the hard way

**The labeler's `layout_type` PATCH loses data.** It looks exactly like the seam to build region
labeling on. Its own docstring says the value is lost on the `Block.to_dict` to `from_dict` round
trip, and it uses a bespoke six-value enum unrelated to either real vocabulary.

**The 43 to 67 percent chapter-opening figure is ambiguous.** It can be read as precision or as
recall, and no evidence file records the calculation. It must be recomputed before anyone builds
on it. Both readings appear in the split design.

## Still open, and the owner's call

- Five decisions in the split design, including whether the glyph inventory moves while its gate
  is open, and how region proposals persist against the labeler's 2026-05-07 scope freeze.
- Gate 3: whether it measures the filtered inventory, whether flagged glyphs stop being emitted,
  or whether a book is admitted at a stated lower number. It was not redefined to pass.
- 490 flat-ascender words across the five books, queued in each manifest and unreviewed.
- The atlas policy. 7.4 MB across five books, and the full corpus would reach roughly 16 million
  glyphs.
- M11's spec and plan still describe NiceGUI behind a supersession banner. Rewrite once the split
  settles, because the review work M11 was sized for is moving to the labeler.

## Operating notes

**A Bash call is capped at ten minutes.** A book runs the full chain in several minutes, so run
one book per call and the largest, `projectID603d7d5e04ca0`, alone.

**Do not adjust the baseline to make the comparison pass.** If Task 5's diff is non-empty, the
difference is the finding. Report which files differ and where the chain first diverges.

## Resume steps

1. Read the plan at `docs/plans/2026-09-06-extract-pgdp-measurement-library.md`.
2. Run Task 0 to capture the baseline, including Step 6, which proves the baseline reproduces.
3. Report Task 0 Step 7's page counts to the owner whatever they show. That is the
   stale-alignment answer.
4. Continue through Tasks 1 to 8 only if Step 6 confirmed determinism.

## Pointers

- Extraction plan: `docs/plans/2026-09-06-extract-pgdp-measurement-library.md`
- Split design: `docs/specs/2026-09-06-measurement-labeling-synthesis-split-design.md`
- Roadmap, both tracks: `docs/plans/README.md`
- Live glyph plan, Gate 3 open: `docs/plans/2026-09-05-pgdp-per-book-glyph-inventory.md`
- Architecture, alignment: `docs/architecture/pgdp-source-line-alignment.md`
- Architecture, profiling: `docs/architecture/pgdp-observed-geometry-profiling.md`
- Architecture, typography: `docs/architecture/pgdp-font-free-typography.md`
- Architecture, glyph inventory: `docs/architecture/pgdp-glyph-inventory.md`
- Architecture, ranking: `docs/architecture/pgdp-ranking-and-review-queue.md`
- Current state: `docs/context/current-state.md`
- Open intent: `docs/context/intent-map.md`
- Tombstones for the five retired plans: `docs/context/decisions.md`
- The library that moves: `src/pdomain_ocr_synth/pgdp/`
- The corpus: `/workspaces/pdomain-data/pgdp-corpus`
- Witness records: `/workspaces/pdomain-data/typography/geometry-v1/`
- Prior evidence, stale for baseline use: `/workspaces/pdomain/.m15f-evidence/`
- Previous handoff: `docs/_archive/handoff/2026-09-06-140411-m15f-gate3-open-and-five-quality-flags.md`
