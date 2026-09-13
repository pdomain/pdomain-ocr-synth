---
kind: handoff
status: "active"
created: "2026-09-13"
created_at: "2026-09-13T17:43:46Z"
owner: CT
branch: master
scope: pgdp-synthesis
worktree: /workspaces/pdomain/pdomain-ocr-synth
base_commit: "3988f53f8633b7e18bdbcfa25dc94ea920c92ee0"
supersedes: "2026-09-09-095107-page-kind-stores-shipped-across-three-repos-merge-decision-open.md"
handoff_reason: user_requested
host: claude-code
---

# Page kind is unblocked, both releases are cut, Task 5 is still unrun

## Read this first

**Every decision the last handoff was waiting on is now made, and both blocking releases
are published.** The three page-kind branches merged, `pdomain-pgdp-measure` has its first
release ever, and `pdomain-book-tools` v0.28.0 is out with the labeler pinned to it.

Tasks 6 and 7 of the page-kind plan are unblocked for the first time. Nothing is in flight,
every repository is clean and pushed, and every gate is green.

**The next piece of work is region-routes Task 5, and after it slice 4.** Task 5 is what
finally makes a proposal appear outside a test. Slice 4 is the geometry engine that makes
those proposals worth reviewing.

## What changed since the last handoff

| what | state |
| --- | --- |
| `feature/page-kind-field` (book-tools) | merged to master |
| `feature/page-class-confidence` (pgdp-measure) | merged to master |
| `feature/page-kind-stores` (labeler) | merged to master |
| `pdomain-pgdp-measure` | released v0.1.0, live on the index |
| `pdomain-book-tools` | released v0.28.0, live on the index |
| labeler's book-tools pin | raised to 0.28.0 |

**The 14 rejected region roles are fixed.** `Block.ALLOWED_BLOCK_ROLE_LABELS` was widened to
all 34 values on 2026-09-08, but that landed after v0.27.0 was tagged, and the labeler pinned
that exact version. The release and pin bump closed it. Verified directly: the engine now
rejects no `RegionRole` value.

**`pdomain-pgdp-measure` had no release path at all.** No CI workflow, no release workflow, no
release scripts. That is why it had never shipped. The path was built before the release was
cut.

## The four decisions, all settled

1. **Merge the three branches.** Merged 2026-09-12, each master green afterwards.
2. **Release `pdomain-pgdp-measure`.** Done, v0.1.0.
3. **Release `pdomain-book-tools`.** Done, v0.28.0, with the labeler pin raised.
4. **Gate 3 on the glyph inventory.** Settled: gate on the filtered inventory, which measures
   0.9942 with every book clear. That was the only route that passes as measured.

A fifth decision was taken for `pdomain-prep-for-pgdp`'s text chain: rewire the stage graph so
hyphen-join reads OCR text directly and wordcheck stays a parallel branch producing flags, and
load parent artifacts by consumer need. Loading by consumer need was mandatory under any
option. The rejected alternative had wordcheck emit page text it did not author.

**The owner also settled slice ordering: build slice 4 before slice 3.** Slice 4 would produce
proposals with no surface to review them, and slice 3 would build a surface with nothing in it.
Build the engine first and drive it over the REST interface.

## The follow-up whose deadline has now expired

**Guard `entry["record"]` in both `proposal_log.py` files before or alongside Task 6.** This was
parked because nothing called those methods. Task 6's handler is the first real caller, so the
parking is over.

Checked on 2026-09-13 and still unguarded in both files:

- `core/page_kind/proposal_log.py` lines 79 and 87
- `core/regions/proposal_log.py` lines 89 and 98

A valid JSON line carrying a correct `"kind"` but no `"record"` raises `KeyError`. Mirror
`reviewed_store.py`'s `try/except (KeyError, ValueError, TypeError)`, fix both files together so
the two journals keep the same shape, and add the wrong-shape test.

**The existing malformed-line test cannot catch this.** It appends `{not json`, which an existing
handler already swallows, so the case that actually breaks the store is never exercised. A test
that cannot fail for the reason it exists is not a gate. This is the third plan in a row where
that exact failure shape mattered.

## Resume steps

1. **Run page-kind Tasks 6 and 7.** Both are unblocked. Land the `proposal_log` guard alongside
   Task 6 rather than after it.
2. **Then region-routes Task 5** on its own: the book-scoped propose route and the
   `propose_regions` job. Confirmed still unrun on 2026-09-13, so every proposal in the system
   is still written by a test. This is the step that changes that.
3. **Then design slice 4 before building it.** The recorded claim that 43 to 67 percent of pages
   show high x-height spread reads either as precision or as recall, and no evidence file records
   the calculation. Recompute it first. Nothing should depend on that figure until it is settled.
4. **Then slice 4 itself**, then slice 3.
5. Use `superpowers:subagent-driven-development`, dispatch `writing-python:python-implementer`
   per task, and run the broad whole-branch review at the end. It has earned its cost twice.
6. Correct the plan whenever execution finds an error in it, and commit that correction.

## What the rest of the session did, and what it changed for you

This was suite-wide dependency and infrastructure work. None of it touches the labeling track's
design, but three parts change how you release and verify.

**There are no GitHub workflows any more.** All 44 were deleted and branch protection removed
across every repository. Releasing now runs entirely from `scripts/release-common.sh`, which
tags, pushes, builds the artifacts and creates the GitHub Release itself.

**Publishing to an index is a manual command with no fallback.** Run
`./scripts/publish-index.sh` in `pdomain-index-pip` or `pdomain-index-npm` after cutting a
release. There is no cron and no dispatch. A release that is not followed by that command stays
invisible to installers, because the indexes are built from release assets.

That gap was not hypothetical: the npm registry had served a stale `@pdomain/pdomain-ui` since
mid-June while two releases sat unindexed.

**Dependencies are current everywhere.** Python lockfiles and declared floors, and the frontend
majors in all five frontend repos, including Tailwind 4. TypeScript is deliberately held at
6.0.3 because no `typescript-eslint` release supports 7 yet; revisit in a few weeks.

## Two defects filed but not fixed

**The device probe raises instead of reporting when the GPU is full.** `_probe_cuda` in
`pdomain-ops` guards only its import, so a saturated card turns `GET /api/suite/device` into a
500 in every suite application. Seven tests across four repositories fail on it whenever the GPU
is busy. Filed at
`pdomain-ops/docs/issues/2026-09-13-gpu-probe-fails-when-the-card-is-full.md`, which also records
what genuinely needs a free GPU.

Nothing on the page-layout OCR critical path needs a local GPU. Region proposals, the review
surface and the geometry engine are all processor work.

**The AppImage installer for `pdomain-ocr-simple-gui` is dead.** Its release script still tries to
dispatch a workflow that no longer exists, guarded by a file check that is now permanently false,
so it silently builds nothing. Either rebuild it locally or accept dropping AppImages.

## Other parked follow-ups, unchanged

- `dict[str, Any]` on every `to_dict`/`from_dict` boundary across `core/page_kind/` and
  `core/regions/`, worth one pass over both together.
- `pdomain-pgdp-measure`'s `tests/` tree carries 1442 basedpyright errors that no gate catches.
  Re-measured 2026-09-13: the source tree is genuinely clean at 0 errors and 229 warnings, and
  the repository's own configuration comment claims 176.
- No test for `PageKindProposal.from_dict` given an invalid `kind` string.
- `Page.page_kind` is a nullable string in the pydantic schema hook with no enum constraint, so
  generated client types call it `string | null` rather than a literal union. Matters only if
  that schema ever feeds codegen for page kind.
- The store-blind payload path at `api/history.py:180`, undo contradicting the decision journal,
  `set_region_word_membership`'s missing mixed-coordinate guard, and `line_structure` digesting
  too little to mark a proposal stale.
- 490 flat-ascender words across five books, queued and unreviewed. The rendering script is
  `render_flat_queue.py` in the workspace-root `.m15f-evidence/` directory.
- The atlas policy, and the table spec's Slice A data model as a prerequisite.

## Operating notes

**`pdomain-book-tools` is in dev-local mode on this machine** because the `[gpu]` extra installs
`opencv-cuda`. Use `make local-upgrade-deps` there, not `make upgrade-deps`, which refuses.

**`pnpm` is not on `PATH`**; it is reached through `mise`, exactly as the Makefiles invoke it.

**Committing needs the venv on `PATH`** or the pre-commit hook fails with `pre-commit not found`.
Prefix with `export PATH="$PWD/.venv-container/bin:$PATH"`.

**Commit subjects must stay within 72 characters** or gitlint rejects the commit.

**Do not add comments to any `tsconfig*.json`.** TypeScript reads them as JSONC, but the
check-json hook enforces strict JSON.

**Long gates get killed under memory pressure.** Run them in the foreground, one at a time.

**Dispatch implementers with the discrepancy instruction and ask for disagreement.** It keeps
paying. This session an implementer refused a briefing of mine that was wrong about dev-local
mode, and another found a real bug in a checker script I wrote.

## Pointers

- The plan with Tasks 6 and 7: `docs/plans/2026-09-08-page-kind-end-to-end.md`
- The plan whose Task 5 is next: `docs/plans/2026-09-08-region-routes-and-proposal-run.md`
- Roadmap with the slice inventory: `docs/plans/2026-09-07-labeling-track-roadmap.md`
- The design every remaining plan argues from:
  `docs/specs/2026-09-07-region-provenance-and-persistence-design.md`
- Region vocabulary: `docs/specs/2026-09-07-region-vocabulary-design.md`
- Still unrun: `docs/plans/2026-09-08-word-and-glyph-provenance.md`,
  `docs/plans/2026-09-08-explicit-membership-and-matching.md`,
  `docs/plans/2026-09-08-style-span-review-surface.md`,
  `docs/plans/2026-09-08-editorial-corrections.md`
- Suite status and agent allocation, written this session:
  `/workspaces/pdomain/pdomain-ops/docs/plans/2026-09-12-suite-status-and-agent-allocation.md`
- Gate 3 recheck: `docs/research/2026-09-07-gate3-recheck-on-the-713-page-alignment.md`
- Current state: `docs/context/current-state.md` — still stale, line 250 still says the split is
  undecided
- The labeler: `/workspaces/pdomain/pdomain-ocr-labeler-spa`
- Previous handoff: the `2026-09-09-095107` file named in this document's `supersedes`
  frontmatter
