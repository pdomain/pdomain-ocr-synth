---
kind: archive
status: retired
created_at: "2026-09-09T09:51:07Z"
owner: "CT"
branch: "master"
scope: "pgdp-synthesis"
worktree: "/workspaces/pdomain/pdomain-ocr-synth"
base_commit: "150fc6929db77ed6a86ddb19a4a18fa29b15c579"
supersedes: "2026-09-08-224245-region-routes-shipped-and-merged-task-5-waits-on-page-kind.md"
handoff_reason: "user_requested"
host: "claude-code"
created: "2026-09-09"
last_verified: "2026-09-13"
---

> **Retired — superseded by `docs/handoff/docs/handoff/2026-09-13-174346-page-kind-unblocked-releases-cut-task-5-still-unrun.md`.**


# Page kind stores shipped across three repos; merge decision open

## Read this first

**Tasks 1 to 5 of the page-kind plan are built, reviewed and gate-green on three unmerged
branches.** Nothing has been merged. The integration menu was presented and not answered, so the
first thing to settle is whether these three branches merge to `master` locally, become PRs, or
wait.

| repo | branch | commits | gate, run by the controller not the implementer |
| --- | --- | --- | --- |
| `pdomain-book-tools` | `feature/page-kind-field` | `da471fd..053d950` | `make AI=1 ci` → passed |
| `pdomain-pgdp-measure` | `feature/page-class-confidence` | `a3910dc..18c64c1` | 1078 passed, ruff clean |
| `pdomain-ocr-labeler-spa` | `feature/page-kind-stores` | `28c68fb..bb249dc` | `make AI=1 ci` → passed |

Each has a worktree at `<repo>/.worktrees/<branch-basename>`, all clean, all forked from `master`.

**Tasks 6 and 7 were deliberately not run.** Each needs a sibling package published to
`pdomain-index-pip`, which is an owner decision and a publish. Task 6 needs `pdomain-pgdp-measure`
released; Task 7 needs `pdomain-book-tools` released with Task 1 in it and the labeler's
`pdomain-book-tools==0.27.0` pin bumped. The previous handoff said Task 7 was unblocked; it is not,
and that is now corrected here.

**Region-routes Task 5 is unblocked as of this branch.** It imports `PageKindProposalLog` and
`PageKindReviewedStore`, which Tasks 4 and 5 here now provide, and it reads page kind through
`getattr(page, "page_kind", None)`, so it does not need the book-tools release. It does need the
labeler branch merged.

## What each task shipped

| task | repo | what |
| --- | --- | --- |
| 1 | book-tools | `Page.page_kind: PageKind \| None`, round-tripping through `to_dict`, `from_dict`, `scale` and the hand-written pydantic schema hook |
| 2 | pgdp-measure | `PageClassification.confidence` and `PageMeasurement.page_class_confidence`, plus the regenerated profile schema |
| 3 | labeler | `core/page_kind/models.py` — `PageKindProposal`, `PageKindProposalRun` |
| 4 | labeler | `core/page_kind/proposal_log.py` — the append-only proposal journal |
| 5 | labeler | `core/page_kind/reviewed_store.py` — the per-page reviewed marker |

## What the final whole-branch review verified that no task review could

It found no Critical and no Important beyond the parked items, and confirmed two cross-repo
contracts by tracing them end to end:

- **The confidence produced in pgdp-measure fits the labeler's validator with no adapter.**
  `_confidence_from_residual` is clamped to `[0, 1]` by construction, and a classifier refusal
  genuinely stays `None` rather than becoming `0.0` — all six `unknown` `PageClassification` call
  sites keep their four-argument form.
- **`PageKind` values containing spaces survive every serialization boundary in all three repos.**
  Nothing splits, trims or slugifies `"chapter opening"`.

It also confirmed Task 6 and 7's plan text calls match the shipped signatures exactly, so those
tasks will not hit drift when they run.

## Three plan defects execution found, all corrected

Two adversarial reviews and a gap scan had missed all three. Corrections are committed here as
`5a94b88` and `150fc69`.

- **`basedpyright` was never green in `pdomain-pgdp-measure`,** though the plan said
  "Expected: PASS". Measured at master `a3910dc`: 1442 errors and 948 warnings, every one inside
  `tests/`, 1037 in `test_pgdp_profile_models.py` alone. `src/` is genuinely 0. The plan now records
  the real bar and forbids the single-site suppression that would have hidden it.
- **Six spec pointers were unresolvable in the repos they were written into.** The plan told Tasks
  1, 3, 4, 5 and 7 to cite a `docs/specs/` path that exists only in this repo. Three independent
  reports raised it. The justification offered for leaving it turned out to be false: the mirrored
  `core/regions/models.py` carries no such path.
- **The reviewed store had two defects in the plan's own code.** A stored `"actor": null` read back
  as the string `"None"`, because the default in `str(d.get("actor", "default"))` only fires on a
  missing key. And any valid JSON object of the wrong shape raised `KeyError` out of
  `is_reviewed()`. Both fixed, both now pinned by tests.

**The reason the second one survived the plan's own gate is worth carrying forward.** Its
malformed-line test appended `{not json`, which an existing handler already caught, so the case
that actually breaks the store was never exercised. A test that cannot fail for the reason it
exists is not a gate. This is the second plan in a row where that specific failure shape mattered.

## The one follow-up with a deadline

**Guard `entry["record"]` in both `proposal_log.py` files before or alongside Task 6.** Today
`runs()`, `proposals_for_run()` and `latest_proposal_for_page()` index it unguarded in
`core/page_kind/proposal_log.py` and identically in the already-merged
`core/regions/proposal_log.py`. A valid JSON line carrying a correct `"kind"` but no `"record"`
raises `KeyError`. This was parked because nothing calls those methods yet — **Task 6's handler is
the first real caller**, so the parking expires when Task 6 lands. Mirror `reviewed_store.py`'s
`try/except (KeyError, ValueError, TypeError)`, fix both files together so the two journals stay
the same shape, and add the wrong-shape test the current malformed-line test never reached.

## Other parked follow-ups, none blocking

- **`dict[str, Any]` on every `to_dict`/`from_dict` boundary** in the three new labeler files,
  matching the shipped `core/regions/models.py`. One reviewer rated it Important, two accepted it.
  Worth one pass across `core/page_kind/` and `core/regions/` together, not one file at a time.
- **`pdomain-pgdp-measure`'s `tests/` tree carries 1442 basedpyright errors no gate catches.** Its
  own `pyproject.toml` comment describes only `src/`, and claims 176 warnings where the real figure
  is 229. Worth a typing pass and an honest gate.
- **No test for `PageKindProposal.from_dict` given an invalid `kind` string.** Coverage only; the
  behaviour is plain `StrEnum` lookup, already proven by the book-tools equivalent.
- **`Page.page_kind` is `NULLABLE_STR_SCHEMA` in the pydantic schema hook with no enum
  constraint,** so generated client types would call it `string | null` rather than a literal
  union. Matches the existing `name`/`page_id` precedent, so not a regression. Matters only if that
  schema ever feeds codegen for page kind.
- Everything carried forward from the previous handoff and not touched this session: the
  store-blind payload path at `api/history.py:180`, undo contradicting the decision journal,
  `set_region_word_membership`'s missing mixed-coordinate guard, and `line_structure` digesting too
  little to mark a proposal stale.

## Owner decisions still open

- **Cut a release of `pdomain-pgdp-measure`.** Blocks Task 6.
- **Cut a release of `pdomain-book-tools`** carrying Task 1, and bump the labeler's
  `pdomain-book-tools==0.27.0` pin. Blocks Task 7. This one was missing from the previous handoff.
- **Merge, PR, or hold the three branches above.**
- Unchanged: `press figure` in the region vocabulary; the table spec's Slice A data model as a
  prerequisite; Gate 3's filtered inventory or a stated lower number, still 0.9942 as measured;
  the atlas policy and M11's spec still describing NiceGUI behind a supersession banner; 490
  flat-ascender words across five books, queued and unreviewed; and widening
  `Block.ALLOWED_BLOCK_ROLE_LABELS` from 20 to the full 34-value `RegionRole` vocabulary, without
  which 14 roles still return `400 invalid_region_role` from every region route.

## Operating notes

**`make ci` fails from a worktree in the labeler and in book-tools.** `uv pip install -e .` ignores
`UV_PROJECT_ENVIRONMENT` and resolves `.venv`, which is absent in a worktree. Run it as
`VIRTUAL_ENV="<repo>/.venv-container" make AI=1 ci`. `pdomain-pgdp-measure` has no Makefile and only
a `.venv-container`; `uv run` there warns that `VIRTUAL_ENV` does not match and ignores it, which is
harmless.

**Commit subjects must stay within 72 characters** or gitlint rejects the commit.

**Committing in this repo needs its venv on `PATH`** or the pre-commit hook fails with
`pre-commit not found`. Prefix with `export PATH="$PWD/.venv/bin:$PATH"`.

**Dispatch implementers with the discrepancy instruction and ask for disagreement.** Every defect
above came from an implementer or reviewer refusing to transcribe without thinking. One implementer
found the `actor: null` bug by noticing the field beside it handled null differently. Another
proved a claim in its own predecessor's report was false by reading the file it cited.

**The SDD ledger is preserved** at `.superpowers/sdd/2026-09-08-page-kind-end-to-end/progress.md`,
against the skill's usual delete-on-clean-review step, because integration is unresolved. It holds
all thirteen rulings with their costs, every parked item, and the per-task commit ranges. Delete it
once the branches land.

## Resume steps

1. Settle the merge decision for the three branches. If merging, the labeler is the one that
   unblocks other work.
2. Get the two release decisions made, or explicitly defer them. They are the only thing standing
   between here and a page kind a human can actually confirm.
3. Then run `docs/plans/2026-09-08-page-kind-end-to-end.md` Tasks 6 and 7, landing the
   `proposal_log.py` guard alongside Task 6 rather than after it.
4. Then region-routes Task 5 alone, which is what finally makes proposals appear in production —
   every proposal in the system today was still written by a test.
5. Use `superpowers:subagent-driven-development`, dispatch `writing-python:python-implementer` per
   task, and run the broad whole-branch review at the end. It earned its cost again this session.
6. Correct the plan whenever execution finds an error in it, and commit that correction.

## Pointers

- The plan just executed, now corrected twice: `docs/plans/2026-09-08-page-kind-end-to-end.md`
- The design every remaining plan argues from:
  `docs/specs/2026-09-07-region-provenance-and-persistence-design.md`
- Region vocabulary: `docs/specs/2026-09-07-region-vocabulary-design.md`
- Roadmap with the plan inventory: `docs/plans/2026-09-07-labeling-track-roadmap.md`
- The plan that needs its Task 5 run: `docs/plans/2026-09-08-region-routes-and-proposal-run.md`
- Still unrun: `docs/plans/2026-09-08-word-and-glyph-provenance.md`,
  `docs/plans/2026-09-08-explicit-membership-and-matching.md`
- The split design this carries out:
  `docs/specs/2026-09-06-measurement-labeling-synthesis-split-design.md`
- Gate 3 recheck: `docs/research/2026-09-07-gate3-recheck-on-the-713-page-alignment.md`
- The SDD ledger, all thirteen rulings:
  `.superpowers/sdd/2026-09-08-page-kind-end-to-end/progress.md`
- Current state: `docs/context/current-state.md` — still stale, line 250 still says the split is
  undecided
- Open intent: `docs/context/intent-map.md`
- The labeler: `/workspaces/pdomain/pdomain-ocr-labeler-spa`
- The measurement package, published, unreleased: `/workspaces/pdomain/pdomain-pgdp-measure`
- Shared primitives: `/workspaces/pdomain/pdomain-book-tools`
- Shared contracts, where `PageKind` lives: `/workspaces/pdomain/pdomain-book-contracts`
- The corpus: `/workspaces/pdomain-data/pgdp-corpus`
- Previous handoff: the `2026-09-08-224245` file in `docs/_archive/handoff/`, named for region
  routes shipping and merging. Its full filename is in this document's `supersedes` frontmatter.
