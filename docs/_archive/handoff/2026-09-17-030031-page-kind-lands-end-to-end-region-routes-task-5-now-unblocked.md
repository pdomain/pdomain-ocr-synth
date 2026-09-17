---
kind: archive
status: retired
created_at: "2026-09-17T03:00:31Z"
owner: "CT"
branch: "master"
scope: "pgdp-synthesis"
worktree: "/workspaces/pdomain/pdomain-ocr-synth"
base_commit: "a6a312df41fe296393037e032124d83cb074cb53"
supersedes: "2026-09-13-174346-page-kind-unblocked-releases-cut-task-5-still-unrun.md"
handoff_reason: "user_requested"
host: "claude-code"
created: "2026-09-17"
last_verified: "2026-09-17"
---

> **Retired — superseded by `docs/handoff/2026-09-17-102343-slice-4-ships-geometry-engine-live-gap-threshold-next.md`.**


# Page kind works end to end, and region-routes Task 5 is finally unblocked

## Read this first

**The page-kind plan is finished and merged.** A classifier now proposes every page's kind into
a durable journal, and a person confirms it onto the page. Until this session every proposal in
the system was written by a test.

**Region-routes Task 5 is the next piece of work, and its blocker is gone.** That task imports
`PageKindProposalLog` and `PageKindReviewedStore`, which did not exist when the region-routes
plan ran. They are on `master` now. Nothing else stands in its way.

**No work has started on Task 5.** The previous session ended immediately after the page-kind
merge. Treat it as untouched.

## What landed

`pdomain-ocr-labeler-spa` `master` is at `a64be5c`, the merge of `feature/page-kind-job`. Six
commits, full suite green on the merged result at 1633 passed and 4 skipped. The worktree and
branch are both deleted.

| commit | what |
| --- | --- |
| `b6ea593` | the `entry["record"]` guard in both `proposal_log.py` files |
| `d59c643` | the `propose_page_kinds` job, its handler registration, and the start route |
| `1835051` | an explicit length check on `classify_pages` output, plus a jittered-confidence test |
| `73dc625` | the confirm route |
| `8cb5a58` | the job kept off the event loop and pinned to its own book |
| `e8f3912` | a confirm that cannot persist now refuses instead of lying |

`pdomain-ocr-synth` `master` is at `a6a312d`, carrying two documentation commits and no code.

**The `entry["record"]` guard landed first, in its own commit, not folded into Task 6.** Both
journals now skip a line that is valid JSON with a correct `"kind"` but no `"record"` key, and
each has a test that feeds exactly that shape. Both tests were confirmed failing with
`KeyError: 'record'` against the pre-fix source.

## The two defects the final review caught

Neither was visible to a task-scoped review, because each needed the whole branch.

**The job blocked the entire server.** `profile_page` is a PIL decode plus numpy work over a full
page scan, and it ran inline in the job coroutine. A 400-page run would have stalled every
request, including the confirm route and the job's own progress stream. Every other
image-touching handler in the labeler already offloads. It now runs through `asyncio.to_thread`.

**The confirm route could return 200 having stored nothing.** If the page payload was not a live
`Page`, or the store was not wired, it set the kind on an object nobody serializes, skipped the
store write, still appended the reviewed marker, and reported success. The durable record then
claimed a human reviewed a page whose kind was never saved. It now resolves through
`_resolve_page_object_for_pages` and returns 503 `store_unavailable` without writing a marker.
The re-review traced every exit path and confirmed `mark_reviewed` has one call site repo-wide,
unreachable without a completed store write.

## Decisions worth knowing

**An invalid page kind returns 400 `validation_error`, not 400 `invalid_page_kind`.** The request
model types `kind` as a `PageKind` with a before-validator running book-contracts'
`normalize_page_kind`, so the generated client gets a real 14-member union instead of `string`.
I checked that `normalize_page_kind` only canonicalizes spelling inside `PageKind`'s own
vocabulary and rejects `normal_recto`, so this is not the vocabulary merge the spec forbids.

**I was wrong that this would be a 422, and an implementer corrected me.** This application maps
every `RequestValidationError` to 400 in `api/middleware/error_handler.py`. Only the geometry
handler returns 422.

**An implementer also found that the plan's own test data could not satisfy its own assertion.**
Task 6 specified page tops of `[300, 302, 298, 301]` while asserting every confidence equals 1.0,
but templates fit on `median(tops)` and confidence is
`max(0.0, 1.0 - residual_px / max(first_band_spread_px, 8))`, so only a zero residual reaches 1.0.

**Dispatching implementers with an explicit instruction to disagree keeps paying.** That is three
sessions running. Keep doing it.

## What went wrong in the doing

**Do not bulk-collapse blank lines in a plan file.** Markdownlint flagged five double-blank lines
after an edit, and a regex that collapsed every run of three or more newlines silently destroyed
PEP 8 spacing inside all the Python code samples, 64 lines of damage. Revert and fix only the
lines the linter named. The fences stayed balanced at 94 either way, so fence-counting does not
catch this.

**Inserting prose after a line number puts it inside the code fence that follows.** Four of five
corrections landed inside `python` blocks on the first attempt. Anchor on the step heading, not
on the line being corrected.

## Parked follow-ups, and where they live now

**Four page-kind follow-ups are filed at
`docs/issues/2026-09-16-page-kind-follow-ups-parked-during-tasks-6-and-7.md`.** That file exists
because the execution ledger recording them was deleted with the plan's workspace. Read it before
building any page-kind surface.

The one that matters most: **the confirmed kind never reaches a plain `GET`.** `_page_payload`
carries neither `page_kind` nor `page_kind_reviewed`, so confirm a kind, reload the page, and it
is gone. The plan deferred this deliberately, and that deferral now stands between this backend
and any review surface.

The other three, in short: a run on a book-labeling project reads images bypassing the manifest
hash pin; the book guard reads an untyped payload key instead of `Job.project_id`; and a failed
persist leaves the kind set in memory with no marker.

## The plan now carries five inline corrections

`docs/plans/2026-09-08-page-kind-end-to-end.md` is marked where execution proved it wrong: the
stale pyproject snippet, the unsatisfiable test data, the missing `asyncio.to_thread`, the error
identifier, and the confirm route's persist-or-refuse shape. Each correction sits in prose ahead
of the code it corrects.

## Resume steps

1. **Run region-routes Task 5** — `core/regions/detector.py`, the `propose_regions` job handler,
   its registration, and `POST /{project_id}/regions/propose`. Its "Not executed" banner and the
   plan's Global Constraints both say it is blocked on the page-kind plan. That is now stale;
   correct both and commit the correction. The constraint says `PageKindProposalLog` must be
   "released", but it lives in `pdomain_ocr_labeler_spa.core.page_kind`, the same package Task 5
   is written into, so merged to `master` is enough and no release is needed.
2. **Then recompute the x-height spread figure before designing slice 4.** The recorded claim
   that 43 to 67 percent of pages show high x-height spread reads either as precision or as
   recall, and no evidence file records the calculation. Nothing should depend on it until it is
   settled.
3. **Then slice 4 itself**, then slice 3. The owner settled that ordering: slice 4 is the
   geometry engine, slice 3 the surface, and building the surface first would leave nothing to
   review in it.
4. **Consider wiring `page_kind` into `_page_payload` before slice 3**, since no review surface
   can display a confirmed kind until that lands.
5. Use `superpowers:subagent-driven-development`, dispatch `writing-python:python-implementer`
   per task, and run the broad whole-branch review at the end. It has now earned its cost three
   times, and this session it found two defects that would have shipped.
6. Correct any plan whenever execution finds an error in it, and commit that correction.

## Still true from the previous handoff

**There are no GitHub workflows.** All 44 were deleted and branch protection removed everywhere.
Releasing runs from `scripts/release-common.sh`.

**Publishing to an index is a manual command with no fallback.** Run `./scripts/publish-index.sh`
in `pdomain-index-pip` or `pdomain-index-npm` after cutting a release, or the release stays
invisible to installers. Note the local `_site/` copy in `pdomain-index-pip` is stale and
generated; the live index is authoritative. I checked the live index directly this session to
confirm `pdomain-pgdp-measure` was there.

**The device probe still raises instead of reporting when the GPU is full**, filed at
`pdomain-ops/docs/issues/2026-09-13-gpu-probe-fails-when-the-card-is-full.md`. Nothing on the
page-layout OCR critical path needs a local GPU.

**The AppImage installer for `pdomain-ocr-simple-gui` is still dead.**

Other parked items carried forward unchanged: `dict[str, Any]` on every `to_dict`/`from_dict`
boundary across `core/page_kind/` and `core/regions/`; `pdomain-pgdp-measure`'s `tests/` tree
carrying 1442 basedpyright errors no gate catches; no test for `PageKindProposal.from_dict` given
an invalid `kind` string; `Page.page_kind` having no enum constraint in the pydantic schema hook;
the store-blind payload path at `api/history.py:180`; undo contradicting the decision journal;
`set_region_word_membership`'s missing mixed-coordinate guard; `line_structure` digesting too
little to mark a proposal stale; 490 unreviewed flat-ascender words across five books; and the
atlas policy with the table spec's Slice A data model as a prerequisite.

## Operating notes

**`tests/unit/.../test_static_mounts.py` fails intermittently under `pytest -n auto`** because
xdist workers share one real `static/` directory. It passes sequentially and in isolation. It is
pre-existing and unrelated to page kind. Do not chase it.

**`pdomain-book-tools` is in dev-local mode on this machine** because the `[gpu]` extra installs
`opencv-cuda`. Use `make local-upgrade-deps` there, not `make upgrade-deps`.

**`pnpm` is not on `PATH`**; it is reached through `mise`, as the Makefiles invoke it. Four
Docker-build tests skip because of this, which is expected.

**Committing needs the venv on `PATH`** or the pre-commit hook fails with `pre-commit not found`.
Prefix with `export PATH="$PWD/.venv-container/bin:$PATH"`.

**Commit subjects must stay within 72 characters** or gitlint rejects the commit.

**Do not add comments to any `tsconfig*.json`.** The check-json hook enforces strict JSON.

**Long gates get killed under memory pressure.** Run them in the foreground, one at a time.

**Adding or changing a route regenerates `frontend/src/api/types.ts`.** That is expected output,
not a hand edit; commit it.

## Pointers

- The plan whose Task 5 is next: `docs/plans/2026-09-08-region-routes-and-proposal-run.md`
- The plan that just finished, now carrying five corrections:
  `docs/plans/2026-09-08-page-kind-end-to-end.md`
- The four parked page-kind follow-ups:
  `docs/issues/2026-09-16-page-kind-follow-ups-parked-during-tasks-6-and-7.md`
- Roadmap with the slice inventory: `docs/plans/2026-09-07-labeling-track-roadmap.md`
- The design every remaining plan argues from:
  `docs/specs/2026-09-07-region-provenance-and-persistence-design.md`
- Region vocabulary: `docs/specs/2026-09-07-region-vocabulary-design.md`
- Still unrun: `docs/plans/2026-09-08-word-and-glyph-provenance.md`,
  `docs/plans/2026-09-08-explicit-membership-and-matching.md`,
  `docs/plans/2026-09-08-style-span-review-surface.md`,
  `docs/plans/2026-09-08-editorial-corrections.md`
- Suite status and agent allocation:
  `/workspaces/pdomain/pdomain-ops/docs/plans/2026-09-12-suite-status-and-agent-allocation.md`
- Gate 3 recheck: `docs/research/2026-09-07-gate3-recheck-on-the-713-page-alignment.md`
- Current state: `docs/context/current-state.md` — still stale, line 250 still says the split is
  undecided
- The labeler: `/workspaces/pdomain/pdomain-ocr-labeler-spa`
- Previous handoff: the `2026-09-13-174346` file named in this document's `supersedes`
  frontmatter
