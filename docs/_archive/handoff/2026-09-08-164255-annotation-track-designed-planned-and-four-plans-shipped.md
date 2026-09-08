---
kind: archive
status: retired
created_at: "2026-09-08T16:42:55Z"
owner: "CT"
branch: "master"
scope: "pgdp-synthesis"
worktree: "/workspaces/pdomain/pdomain-ocr-synth"
base_commit: "1f8a0ee6d118c8b5d5c848ffdf5d648d08c7b77e"
supersedes: "2026-09-07-131242-labeling-track-opened-and-region-vocabulary-settled.md"
handoff_reason: "user_requested"
host: "claude-code"
created: "2026-09-08"
last_verified: "2026-09-08"
---

> **Retired — superseded by `docs/handoff/2026-09-08-224245-region-routes-shipped-and-merged-task-5-waits-on-page-kind.md`.**


# The annotation track is designed, planned, and four plans are shipped

## Read this first

**The design is finished and nine plans exist. Four are executed, merged, and pushed.** Everything
below is either a remaining plan, a gap with no plan, or an owner decision.

The design grew well past "where do region proposals live". It settled into one rule applied at
five annotation levels: **keep what the machine said beside what the person decided, and never let
either overwrite the other.** Editorial corrections are the same rule on a different axis: keep what
the ink says beside what it should say.

## What shipped, and where

Four repositories, all pushed. `pdomain-pgdp-measure` was published this session; it had no remote
and no license before.

| repo | head | what landed |
| --- | --- | --- |
| `pdomain-book-contracts` | `bfcb7dd`, released `v0.2.0` | the shared vocabularies |
| `pdomain-book-tools` | `da471fd` | 34-role `Block`, duplication check, folio fix |
| `pdomain-ocr-labeler-spa` | `4db27de` | the three region stores and the resolver |
| `pdomain-pgdp-measure` | `a3910dc`, newly published | page template spread |

`pdomain-book-contracts` v0.2.0 is on `pdomain-index-pip`, so every downstream repo resolves the
vocabulary normally. No git-rev pins remain.

## The five plans still to execute

Read each plan before starting it; they carry real code and exact commands.

1. **Region routes and the proposal run**, 7 tasks —
   `docs/plans/2026-09-08-region-routes-and-proposal-run.md`. Needs the region stores, which
   shipped. This is the next natural step.
2. **Word and glyph provenance**, 7 tasks — `docs/plans/2026-09-08-word-and-glyph-provenance.md`.
3. **Page kind end to end**, 7 tasks — `docs/plans/2026-09-08-page-kind-end-to-end.md`. Its Task 6
   has the labeler depend on `pdomain-pgdp-measure` as a package. That repo is now published but
   has **no release**, so it needs the same `scripts/do-release.sh` treatment book-contracts got
   before this task can work.
4. **Explicit membership and matching**, 3 tasks —
   `docs/plans/2026-09-08-explicit-membership-and-matching.md`.
5. **Style span review surface**, 4 tasks — `docs/plans/2026-09-08-style-span-review-surface.md`.
   Gates Tasks 2 to 5 of the editorial corrections plan.

**Editorial corrections**, 5 tasks — `docs/plans/2026-09-08-editorial-corrections.md`. Its
vocabularies dependency is satisfied; only the style-span plan still gates it.

## Gaps with no plan at all

- **The post-processor that applies editorial corrections.** Its input shape is settled in the
  design; nothing else about it is.
- **Whether an editorial correction can span a page boundary.** A word broken across pages is
  already handled poorly, and a correction to one is unmodeled.
- **The labeled-dataset contract the synthesizer reads at M16.** Still unspecified, and it is the
  join between the two halves of the suite.
- **Slices 3 to 7 of the labeling track.** Unplanned by intent: each needs its own design first.
  See `docs/plans/2026-09-07-labeling-track-roadmap.md`.

## Owner decisions still open

- **Cut a release of `pdomain-pgdp-measure`.** Blocks page kind Task 6. The repo now has a remote
  and an Unlicense; it has never been released.
- **`press figure` in the region vocabulary.** Real but narrow, and nothing downstream asks for it.
- **The table spec's Slice A data model as a prerequisite**, so the corpus carries cell structure
  from the first page rather than being relabeled later.
- **Gate 3 itself:** the filtered inventory, or a stated lower number. Unchanged from the previous
  handoff. Filtering remains the only route that passes as measured, at 0.9942.
- **The atlas policy**, and M11's spec still describing NiceGUI behind a supersession banner.
- **490 flat-ascender words** across five books, queued and unreviewed.

## Rulings made this session, so they are not relitigated

- Regions are first-class `Block` objects, not sidecars, and they **nest**. Hierarchy is expressed
  by nesting.
- A region's box is **not** its membership. Sibling regions may overlap as rectangles and share no
  word; ancestry is the only multi-membership.
- Words and glyphs get the same treatment as regions. All five levels must be built to the same
  standard with no level left short.
- **Staleness is decided per edit kind**, not per page. A run records a digest per page facet it
  read; a text correction leaves geometry proposals valid.
- **An accepted decision carries across runs**, recorded as its own `carried` disposition naming
  both runs, so a model upgrade does not re-review the corpus and a carried decision is never
  counted as fresh human agreement.
- Two models eventually replace PP-DocLayout: one book-scoped for page kind, one page-scoped for
  regions.
- Editorial corrections never enter `ground_truth_text`. The labeler records them; a post-processor
  applies them.

## What execution found that review did not

Seven real errors in plans that had been adversarially reviewed and gap-scanned twice. All are
corrected in the plans now. The pattern is worth keeping: **run the code early, and require
implementers to report discrepancies rather than work around them.**

The one that mattered most: `find_duplicated_words` treated a signature going from absent to present
as duplication. It is creation. The pipeline legitimately synthesizes words — the cursive drop-cap
recovery builds a glyph the recognizer missed entirely — so under `PD_OCR_REORGANIZE_STRICT` the
check would have raised on any book where OCR missed a drop cap, which is exactly the historical
typography this project exists for.

Also worth remembering: **green CI proved nothing** for the resolver. 1542 backend and 1637 frontend
tests passed on wrong behaviour, because the failing assertion was the plan's and the implementer
made the code satisfy it. Reading the semantics against how a person actually reviews a page is what
caught it.

## Operating notes

**Run `make ci` with the venv on PATH** in this repo: prefix `PATH="$PWD/.venv-container/bin:$PATH"`,
or a bare `git commit` fails with `pre-commit not found`.

**Commit subjects must stay within 72 characters** or gitlint rejects the commit.

**`make ci` in `pdomain-book-tools` needs `CI=1`** in this sandbox. `nvidia-smi` reports a device but
CUDA allocation fails. Measured on pristine master: 2910 passed, 24 failed, every failure in one of
five GPU test files, every cause a driver or allocation fault. `CI=1` is the Makefile's own switch
and is what real CI sets.

**Two pre-existing test failures are not yours.** `test_torch_cuda_basic` in book-tools and
`test_suite_device_route_is_mounted` in the labeler both fail on pristine master for the same CUDA
reason.

**The basedpyright venv trap is fixed** in all four repos. `venvPath`/`venv` no longer point at a
`.venv` that nothing else uses. If a wall of missing-attribute errors ever reappears, suspect the
environment before the code.

**`feature/edition-companion-contract` is still open** in the labeler and touches the book labeling
manifest, the same area the region proposal run needs when it goes book-scoped. The collision was
predicted and has not happened yet; region routes is the plan that would trigger it.

## Resume steps

1. Read `docs/specs/2026-09-07-region-provenance-and-persistence-design.md` first. It is the
   design, 693 lines, and every plan argues from it.
2. Execute the region routes plan next. It is the largest remaining piece of slice 2 and four other
   plans are easier once the routes exist.
3. Dispatch `writing-python:python-implementer` with `isolation: "worktree"` per plan, and pass it
   the discrepancy instruction: fix the code to match the plan's intent, then report what the plan
   said versus what was true. That instruction is what surfaced all seven errors.
4. Integrate with `superpowers:finishing-a-development-branch`. Verify the merged result before
   cleanup, and re-sync the venv if typecheck reports missing attributes.
5. Correct the plan whenever execution finds an error in it, and commit that correction. Every one
   so far has been worth recording.

## Pointers

- The design, all five levels: `docs/specs/2026-09-07-region-provenance-and-persistence-design.md`
- Region vocabulary, section one: `docs/specs/2026-09-07-region-vocabulary-design.md`
- Roadmap with the plan inventory: `docs/plans/2026-09-07-labeling-track-roadmap.md`
- The nine plans: `docs/plans/2026-09-08-*.md`
- The split design this carries out: `docs/specs/2026-09-06-measurement-labeling-synthesis-split-design.md`
- Gate 3 recheck: `docs/research/2026-09-07-gate3-recheck-on-the-713-page-alignment.md`
- Current state: `docs/context/current-state.md` — **stale**, line 250 still says the split is
  undecided and nothing has moved
- Open intent: `docs/context/intent-map.md`
- The labeler: `/workspaces/pdomain/pdomain-ocr-labeler-spa`
- The measurement package, newly published: `/workspaces/pdomain/pdomain-pgdp-measure`
- Shared contracts: `/workspaces/pdomain/pdomain-book-contracts`
- Shared primitives: `/workspaces/pdomain/pdomain-book-tools`
- The corpus: `/workspaces/pdomain-data/pgdp-corpus`
- Previous handoff: `docs/_archive/handoff/2026-09-07-131242-labeling-track-opened-and-region-vocabulary-settled.md`
