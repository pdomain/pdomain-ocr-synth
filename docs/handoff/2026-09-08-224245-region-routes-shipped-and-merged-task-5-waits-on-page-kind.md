---
kind: handoff
status: "active"
created: "2026-09-08"
created_at: "2026-09-08T22:42:45Z"
owner: CT
branch: master
scope: pgdp-synthesis
worktree: /workspaces/pdomain/pdomain-ocr-synth
base_commit: "ee4521839211da4661b8ab5ed45fa3d92953a1e9"
supersedes: "2026-09-08-164255-annotation-track-designed-planned-and-four-plans-shipped.md"
handoff_reason: stopping
host: claude-code
---

# Region routes shipped and merged; Task 5 waits on page kind

## Read this first

**Five of the nine annotation plans are now executed.** The region routes plan is merged into
`pdomain-ocr-labeler-spa` master at `28c68fb`, full gate green. Seven of its eight routes shipped.

**Task 5 of that plan did not ship, and it is the one thing that makes the feature real.** It
imports `core/page_kind/proposal_log.py` and `core/page_kind/reviewed_store.py`, which the
page-kind-end-to-end plan builds and which do not exist. Until it lands, **nothing populates the
proposal journal in production** — every proposal in the system today was written by a test. The
routes to accept and reject proposals work; there is simply nothing to accept yet.

That makes the ordering for the next session concrete: run the page-kind plan, then come back and
execute Task 5 alone.

## What is in master now

`pdomain-ocr-labeler-spa` at `28c68fb`, merged from `feature/region-routes-and-proposal-run`
(16 commits, branch and worktree deleted). Backend 1617 passed / 5 skipped, frontend 1637,
`make ci` green on the merged result.

| what | where |
| --- | --- |
| `Block` → `ResolvedRegion` adapter, facet digests | `core/regions/block_adapter.py` |
| Seven routes: create, edit, delete, membership, list/accept/reject proposals | `api/regions.py` |
| `PagePayload.regions` / `.proposals`, resolved per request | `api/pages.py` |
| Two canvas layers, proposals visibly unlike decisions | `frontend/src/components/BBoxOverlay.tsx`, `PageImageCanvas.tsx` |
| Golden fixture pinning the `Block` round trip | `tests/conformance/test_region_block_round_trip.py` |

## The next four plans, in the order that unblocks the most

1. **Page kind end to end**, 7 tasks — `docs/plans/2026-09-08-page-kind-end-to-end.md`. Do this
   next. Its Tasks 3 to 5 build the `core/page_kind` stores that region-routes Task 5 imports. Its
   own Task 6 still needs a `pdomain-pgdp-measure` release, which is an open owner decision, but
   Tasks 1 to 5 and 7 do not.
2. **Region routes Task 5 only** — `docs/plans/2026-09-08-region-routes-and-proposal-run.md`. The
   plan carries an execution-status banner saying exactly this. One task: the `propose_regions` job,
   the `null_region_detector` seam, and `POST /regions/propose`.
3. **Word and glyph provenance**, 7 tasks — `docs/plans/2026-09-08-word-and-glyph-provenance.md`.
   It also owns the `stable_word_id` flaw described below.
4. **Explicit membership and matching**, 3 tasks —
   `docs/plans/2026-09-08-explicit-membership-and-matching.md`; then **style span review surface**,
   4 tasks, which gates Tasks 2 to 5 of **editorial corrections**.

## What execution found that two adversarial reviews had not

Every task found at least one real error in a plan that had been reviewed twice and gap-scanned.
The plan is corrected for all of them, across six commits in this repo ending `ee45218`. The four
worth carrying forward as a pattern:

- **A route wrote a page blob that could not be read back.** `edit_region` assigned
  `block_role_labels` directly. That attribute does not validate — only `Block.__init__` does — and
  `Block.from_dict` builds through the validating constructor, so a PATCH carrying one of the 14
  roles `book-tools` does not yet allow produced an unloadable page.
- **Accepting a proposal twice made two confirmed regions.** A double click was enough.
- **A frontend colour edit never reached the canvas.** Rendering resolves through
  `resolveLayerColorSpec`'s switch, which the plan never mentioned, so the two new layers were
  defined and never painted.
- **A test could not fail for the reason it existed.** The Playwright check asserted only that two
  sampled pixels differ, which passes for one hue at two alphas. Tightening it to a per-layer hue
  band then exposed that the confirmed sample had been sitting under a viewport-mode pill all
  along, contaminated by ~29 RGB units.

**The final whole-branch review earned its cost and nothing before it did.** It found a Critical the
six task reviews missed: `Block.lines` returns `[self]` for a `WORDS`-typed block, so a leaf region
is itself an entry in `page.lines`. Moving a word out of another region made that region the
`owner_line`, and `remove_item` recomputed its box. If the moved word was its last, the box became
`None`, `confirmed_regions_from_page` skipped it, and the region vanished from the payload while
still living in the blob — invisible, undeletable, still serialized. Run the broad review.

## Parked follow-ups, none blocking

- **`api/history.py:180`** calls `_page_payload` without `page_store` on undo/redo — the last
  store-blind payload path. Not observable today because history markers write one blob ref.
- **Undo can contradict the decision journal.** Accept, delete, undo restores the confirmed region
  while the latest decision says rejected. The mirror case predates this branch and history routes
  append nothing to the journal at all. Whoever makes history decision-aware owns both directions.
- **`set_region_word_membership` has no mixed-coordinate guard**, so `Block.add_item`'s
  coordinate-uniformity `ValueError` still surfaces as a 500 there. The other three region routes
  were corrected.
- **`line_structure` digests only `[block_category, override_page_sort_order]` per line**, so it
  never encoded which words belong to which line, and a membership write marks no proposal stale.
  The spec's facet table says it covers "line and paragraph grouping". Raise against the spec.
- **`stable_word_id` derives from `reading_order`**, and persisted typography corrections are keyed
  by it, so a membership write silently detaches them. Pre-existing —
  `lines_paragraphs.py`'s merge and split already restructure `page.lines` — and owned by the
  word-and-glyph-provenance plan. `tests/integration/test_region_membership_word_identity.py` pins
  the current behaviour so it is not rediscovered by accident.

## Owner decisions still open

Unchanged from the previous handoff except where noted.

- **Cut a release of `pdomain-pgdp-measure`.** Blocks page-kind Task 6, which is now the next plan.
- **`press figure` in the region vocabulary.** Real but narrow.
- **The table spec's Slice A data model as a prerequisite.**
- **Gate 3: the filtered inventory, or a stated lower number.** Filtering remains the only route
  that passes as measured, at 0.9942.
- **The atlas policy**, and M11's spec still describing NiceGUI behind a supersession banner.
- **490 flat-ascender words** across five books, queued and unreviewed.
- **Widening `Block.ALLOWED_BLOCK_ROLE_LABELS`** from 20 to the full 34-value `RegionRole`
  vocabulary, in `pdomain-book-tools`. Until it lands, 14 roles return `400 invalid_region_role`
  from every region route. This is now load-bearing rather than theoretical.

## Operating notes

**`make ci` fails from a worktree in the labeler.** `uv pip install -e .` ignores
`UV_PROJECT_ENVIRONMENT` and resolves `.venv`, which is absent or empty in a worktree. Run it as
`VIRTUAL_ENV="$PWD/.venv-container" make AI=1 ci`. Plain `make AI=1 test`, `make AI=1 lint` and
`make openapi-export` work unprefixed.

**Commit subjects must stay within 72 characters** or gitlint rejects the commit. Several subjects
suggested in these plans exceeded it; the region-routes plan's are all corrected.

**11 `make e2e` failures in the labeler are pre-existing.** Confirmed by name against master with
no branch changes present: style-toolbar, export-manifest, parity and coverage tests, all failing
with `Aggregate ... version None not found`. Do not re-litigate them.

**Any route that adds or changes a route or a payload field must run `make openapi-export`** and
commit `frontend/src/api/types.ts`, or the `openapi-drift` job goes red.

**Dispatch implementers with the discrepancy instruction**: fix the code to match the plan's intent,
then report what the plan said versus what was true. That instruction is what surfaced every error
above. Ask for disagreement too — two of this session's best outcomes came from an implementer
refusing an instruction with evidence, including a test I specified that was unreachable.

## Resume steps

1. Read `docs/specs/2026-09-07-region-provenance-and-persistence-design.md` if you have not. It is
   the design and every remaining plan argues from it.
2. Execute `docs/plans/2026-09-08-page-kind-end-to-end.md`. Tasks 1 to 5 and 7 are unblocked; Task 6
   needs the `pdomain-pgdp-measure` release decision.
3. Then execute region-routes Task 5 alone. Its brief is unchanged and the plan's banner explains
   the dependency.
4. Use `superpowers:subagent-driven-development` per plan, dispatch
   `writing-python:python-implementer` per task, and run the broad whole-branch review at the end —
   it caught what six task reviews did not.
5. Correct the plan whenever execution finds an error in it, and commit that correction. Every one
   so far has been worth recording.

## Pointers

- The design, all five levels: `docs/specs/2026-09-07-region-provenance-and-persistence-design.md`
- Region vocabulary, section one: `docs/specs/2026-09-07-region-vocabulary-design.md`
- Roadmap with the plan inventory: `docs/plans/2026-09-07-labeling-track-roadmap.md`
- The plan just executed, with its status banner: `docs/plans/2026-09-08-region-routes-and-proposal-run.md`
- The plan to run next: `docs/plans/2026-09-08-page-kind-end-to-end.md`
- The split design this carries out: `docs/specs/2026-09-06-measurement-labeling-synthesis-split-design.md`
- Gate 3 recheck: `docs/research/2026-09-07-gate3-recheck-on-the-713-page-alignment.md`
- Current state: `docs/context/current-state.md` — **stale**, line 250 still says the split is
  undecided and nothing has moved
- Open intent: `docs/context/intent-map.md`
- The labeler, now at master `28c68fb`: `/workspaces/pdomain/pdomain-ocr-labeler-spa`
- The measurement package, published, unreleased: `/workspaces/pdomain/pdomain-pgdp-measure`
- Shared contracts: `/workspaces/pdomain/pdomain-book-contracts`
- Shared primitives: `/workspaces/pdomain/pdomain-book-tools`
- The corpus: `/workspaces/pdomain-data/pgdp-corpus`
- Previous handoff: `docs/_archive/handoff/2026-09-08-164255-annotation-track-designed-planned-and-four-plans-shipped.md`
