---
kind: archive
status: retired
created_at: "2026-09-07T10:25:40Z"
owner: "CT"
branch: "master"
scope: "pgdp-synthesis"
worktree: "/workspaces/pdomain/pdomain-ocr-synth"
base_commit: "5b3d55d44083063ac2613b3a6228114da3c31a6d"
supersedes: "2026-09-06-214111-measurement-library-extraction-planned-and-ready.md"
handoff_reason: "user_requested"
host: "claude-code"
created: "2026-09-07"
last_verified: "2026-09-07"
---

> **Retired — superseded by `docs/handoff/2026-09-07-131242-labeling-track-opened-and-region-vocabulary-settled.md`.**


# The extraction shipped, and Gate 3 is the open item

## Read this first

**Nothing is blocked, and nothing is half-done.** The measurement library is extracted, verified
byte for byte, and removed from this repository. All nine tasks of the extraction plan and all
seven of its verification items pass. Both repositories are clean, and nothing is pushed.

The next decision is Gate 3, and it needs a person, not another measurement run.

## What exists now

`pdomain-pgdp-measure` is a real package at `/workspaces/pdomain/pdomain-pgdp-measure`, eight
commits, never pushed. It owns scan geometry, alignment, typography, and glyph cutting, and the
`pgdp-measure` CLI with subcommands `rank`, `profile`, `align`, `typography`, and `glyphs`.

This repository renders synthetic pages and publishes them. It consumes measurement reports and no
longer produces them.

| repository | tests | gate |
| --- | --- | --- |
| `pdomain-ocr-synth` | 797 pass | `make ci AI=1` green |
| `pdomain-pgdp-measure` | 1068 pass, 90.2% coverage | ruff, ruff format, basedpyright recommended, 0 errors |

Both report 0 dangling references under `docgraph check --strict`.

## The extraction is verified, and here is exactly what that means

All 927 report files across the five books reproduce against the baseline captured at `f9fdfef`,
before anything moved.

**Two provenance fields are normalized, and only two.** `tool_version` is the package's own VCS
version, so it must change. `alignment_sha256` hashes `alignment.json`, which carries
`tool_version`, so it moves for that reason alone. That dependence was proven, not assumed: on all
five books the recorded `alignment_sha256` equals the raw sha of `alignment.json`, and the two
alignment files hash identically once `tool_version` is normalized. `profile_sha256`,
`rows_sha256`, and `geometry_sha256` are deliberately left alone.

Every measured value is identical. One typography report differs in 2 of 29,680 leaf values,
another in 2 of 59,517, and both times the two are those provenance fields. Every atlas PNG and
every `glyphs.jsonl` matched with no normalization at all.

`rank` was checked separately, because the acceptance run consumes a frozen ranking and never
exercises it. 0 differing across all 328 shared projects.

## Gate 3 is the open item, and re-running the chain will not close it

**All 23 glyphs the M15f review marked wrong survive the band-identification fixes.** Not one is
removed. The fixes are worth 48 accepted pages and zero mislabels. That closes the hypothesis
carried in three previous handoffs.

**0.978 is an upper bound on the error, because the review sheet hides the style.** Three of the 23
marks are `small_caps` records that describe the ink exactly. The sheet shows a reviewer the
character alone, so a small-capital N labelled `n` reads as an error when the record is right.

Two of the six unflagged survivors are real defects the quality flags miss. Cell `s12` is a
within-word cut that puts `s` on a well-formed `e`. Cell `e5` is a missed word gap in a script
italic that puts `e` on the three letterforms "ler". Three more, `e13`, `h21`, and `a10`, read as
correctly cut at nine times scale and want a second opinion before being called review errors.

The full finding is `docs/research/2026-09-07-gate3-recheck-on-the-713-page-alignment.md`.

## A trap that inverted a whole analysis, recorded so it does not happen twice

**`line_ordinal` is renumbered by the band-identification fixes, even for glyphs that never
moved.** Match glyphs across inventories by page and box, or by `source_line_ordinal`.

A first pass of the Gate 3 recheck matched on `line_ordinal` and reported 4 of 23 marks as removed
and a 16 percent sampling-pool turnover. Both were fabrications. The renumbering is small enough to
look like nothing: cell `e5` sits at 19 before and 21 after, with an identical box, character,
flags, and `source_line_ordinal`. A reviewer caught it by checking two specific glyphs against both
files. No amount of re-reading the numbers would have exposed it.

## What the plan got wrong, since the same shapes will recur

Every task needed correction against reality:

- Task 0's capture script ranked per book using flags that select no book. Neither `rank-pgdp` nor
  `profile-pgdp` took a book selector; a book is isolated by cutting the ranking.
- The ranking has to be frozen. The corpus is live and grew from 330 projects to 390 during the
  work, and a new project changes the ranking header sha that every later stage chains.
- Task 1's pyproject carried no tool config, which would have graded the moved code against ruff
  and basedpyright defaults rather than the settings it was written to pass.
- 32 modules, not 33, with absolute self-imports throughout rather than relative.
- `tests/__init__.py` had to come across, and ten test files needed the CLI, not five.
- Byte identity could not pass literally, because `tool_version` is written into three report
  types.

## Three of five split decisions are closed

- The package name is `pdomain-pgdp-measure`, decided 2026-09-06.
- The glyph inventory moved with the rest, decided 2026-09-07. Gate 3 being open stopped being a
  reason to wait once the recheck showed no measurement change will move it.
- No transition dependency, decided 2026-09-07. This repository cut over in one step, imports
  nothing from the package, and names it nowhere in `pyproject.toml`.

Still open: how region proposals persist against the labeler's 2026-05-07 scope freeze, and
whether the labeler ingests PGDP corpora directly or only reads measurement reports.

## Still open, and the owner's call

- Gate 3. Show `label_style` on the review sheet and rescore before deciding it. The choice is
  unchanged, but the number it is made against is not.
- Re-read `e13`, `h21`, and `a10` before treating them as review false positives.
- 490 flat-ascender words across the five books, queued in each manifest and unreviewed.
- The atlas policy. 7.4 MB across five books, and the full corpus would reach roughly 16 million
  glyphs.
- M11's spec and plan still describe NiceGUI behind a supersession banner.
- Nothing is pushed in either repository, and `pdomain-pgdp-measure` has no remote.

## Operating notes

**A Bash call is capped at ten minutes, but background calls are not.** All five books ran
concurrently on the 20-core box at under 1 GB each. Wall clock was 230, 579, 625, 724, and 1032
seconds for the baseline, and 241 through 1096 for the verification.

**Run `make ci` with the venv on PATH.** A bare `git commit` failed once with `pre-commit not
found`; prefixing `PATH="$PWD/.venv-container/bin:$PATH"` fixed it.

**basedpyright gates on errors, not warnings.** `make typecheck` uses `--level error`. A bare
invocation applies `failOnWarnings` and fails on 176 informational warnings.

## Resume steps

1. Read `docs/research/2026-09-07-gate3-recheck-on-the-713-page-alignment.md` before touching
   Gate 3. It rules out the re-run hypothesis and explains why the current number is inflated.
2. To act on Gate 3, edit the review sheet renderer to show `label_style` beside the character,
   then re-render and rescore. The renderer is `/workspaces/pdomain/.m15f-evidence/gate3.py`.
3. For anything comparing two glyph inventories, match on page and box. Working scripts are in
   `/workspaces/pdomain/.gate3-recheck/`.
4. The extraction needs nothing further. Push both repositories only on the owner's say-so.

## Pointers

- Extraction plan, shipped: `docs/plans/2026-09-06-extract-pgdp-measurement-library.md`
- Gate 3 recheck: `docs/research/2026-09-07-gate3-recheck-on-the-713-page-alignment.md`
- Split design, three decisions closed: `docs/specs/2026-09-06-measurement-labeling-synthesis-split-design.md`
- Roadmap, both tracks: `docs/plans/README.md`
- Current state: `docs/context/current-state.md`
- Open intent: `docs/context/intent-map.md`
- Tombstones for the moved docs: `docs/context/decisions.md`
- The new package: `/workspaces/pdomain/pdomain-pgdp-measure`
- Its architecture docs and live glyph plan: `/workspaces/pdomain/pdomain-pgdp-measure/docs/`
- Baseline, 927 files: `/workspaces/pdomain/.extraction-baseline/`
- Verification run and the manifest normalizer: `/workspaces/pdomain/.extraction-verify/`
- Gate 3 recheck scripts and rendered crops: `/workspaces/pdomain/.gate3-recheck/`
- The M15f review sheet renderer: `/workspaces/pdomain/.m15f-evidence/gate3.py`
- The corpus, now 390 projects: `/workspaces/pdomain-data/pgdp-corpus`
- Witness records: `/workspaces/pdomain-data/typography/geometry-v1/`
- Previous handoff: `docs/_archive/handoff/2026-09-06-214111-measurement-library-extraction-planned-and-ready.md`
