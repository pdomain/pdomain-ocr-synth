---
kind: handoff
status: "active"
created: "2026-09-02"
created_at: "2026-09-02T21:02:55Z"
owner: CT
branch: master
scope: pgdp-synthesis
worktree: /workspaces/pdomain/pdomain-ocr-synth
base_commit: "9f13c0dda6dbd38a96acb1abd55cbe0469c1dcad"
supersedes: "2026-08-31-183553-m15b-gates-pass-and-merged.md"
handoff_reason: user_requested
host: claude-code
---

# M15b residuals fixed, and this repo keeps its F2 parser

## Goal

Reach M15: fit typography from an aligned page, and synthesise a page from a book
profile. Nothing in that goal is started. Everything below is what cleared the
way.

## Done since the last handoff

Both residual alignment errors on `projectID603d7d5e04ca0` are fixed, and
accepted-line precision re-measured at 1.0000 over 760 rows.

Three band-identification defects caused them. Head-band selection now picks the
running head by position rather than by band ordinal, so a chapter opening no
longer matches its head to a body source line. A decorative rule band is now
recognised as a rule instead of a match candidate. The speck test had to be
narrowed at the same time: removing the rule band alone made `379.png` worse,
going from two wrong matches to about twenty-nine.

The ledger could not be reused across this change. It keys errors by position
among a page's matches, and moving band identification moved every position, so
the whole thing was re-measured.

## The contracts extraction, and what it means here

`pdomain-book-contracts` v0.1.0 now exists and holds the pure-Python contracts
that used to live in `pdomain-book-tools`, including a full PGDP F2 parser.
This repo does **not** adopt it, and that is a deliberate decision rather than
work left undone.

`src/pdomain_ocr_synth/pgdp/f2.py` takes a mapping of every page at once and
carries block state across page boundaries, so a `/# #/` block that opens on one
page and closes several pages later has its body stitched onto each page it
spans. Two tests cover exactly that. The contracts parser takes a single page key
and has no concept of page order, so it would emit an unclosed-block warning and
drop those bodies instead.

The output shapes differ too. This repo's parser returns raw markup text that
`features.py` runs regexes over and `ranking.py` builds diagnostics from. The
contracts parser returns a decoded `TypographyPageRecord`. Adopting it means
rewriting three callers, which is a redesign.

The duplication is real. Removing it needs a decision about whether the contracts
parser should grow a document-scoped mode, and that is separate work.

## One caution is now obsolete

The previous handoff said to preserve `.venv-container` during CI by moving it to
a temporary directory, because left in place it enters the source distribution and
fails the build. Do not do that dance any more. The cause is fixed: `uv build`
was sweeping the directory into the sdist, where its absolute symlink to the
uv-managed interpreter cannot be unpacked, and `pyproject.toml` now excludes both
venv directories the way `pdomain-book-tools` always did.

## Still not done

- The 30-page book admission minimum is still an uncalibrated seed. It cannot be
  calibrated until something downstream states how many pages a per-book
  typography fit actually needs.
- Nothing fits typography from an aligned page, and nothing synthesises a page
  from a book profile. That is M15 and none of it is started.
- This repo has 115 commits on `master` that have never been pushed to its
  remote. Someone should decide whether that is deliberate.

## Resume steps

1. Read `docs/plans/` for the M15 synthesis milestone and propose an end-to-end
   plan before writing code, per this repo's own rule.
2. Decide the 30-page minimum as part of that plan, since the plan is what will
   finally say how many pages a fit needs.
3. Leave `f2.py` alone unless you are taking on the document-scoped parser
   question deliberately.

## Pointers

- [previous handoff](2026-08-31-183553-m15b-gates-pass-and-merged.md)
- [book-contracts extraction plan](../../../pdomain-ops/docs/plans/2026-09-01-extract-book-contracts-and-retire-pd-repos.md)
