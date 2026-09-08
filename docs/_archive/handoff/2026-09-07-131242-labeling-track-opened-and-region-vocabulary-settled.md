---
kind: archive
status: retired
created_at: "2026-09-07T13:13:00Z"
owner: "CT"
branch: "master"
scope: "pgdp-synthesis"
worktree: "/workspaces/pdomain/pdomain-ocr-synth"
base_commit: "74f41d32379588f3519a0222d464c0ac930c31b2"
supersedes: "2026-09-07-102549-measurement-library-extracted-and-gate-3-recheck.md"
handoff_reason: "user_requested"
host: "claude-code"
created: "2026-09-07"
last_verified: "2026-09-08"
---

> **Retired — superseded by `docs/handoff/2026-09-08-164255-annotation-track-designed-planned-and-four-plans-shipped.md`.**


# The labeling track is open and its vocabulary is settled

## Read this first

**The focus moved.** Gate 3 is closed as far as measurement can take it, and the owner redirected
the session to the labeling side: build region labeling into `pdomain-ocr-labeler-spa`, and get
that whole side done before the synthesizer consumes anything.

Nothing is blocked. Four commits landed, all documentation. No code has moved in any repository.

## What closed this morning

**Showing `label_style` does not close Gate 3, and that question is finished.** The review sheet
now captions every cell with its style, the CSV carries the column, and the same 1,050 cells were
rescored with all 23 marks carried forward.

| book | as marked | small caps | corrected |
| --- | ---: | ---: | ---: |
| projectID657550412c8dc | 1.0000 | 0 | 1.0000 |
| projectID609bfa0449bdf | 0.9952 | 0 | 0.9952 |
| projectID64a479f51ce5b | 0.9905 | 0 | 0.9905 |
| projectID603d7d5e04ca0 | 0.9619 | 3 | 0.9762 |
| projectID67a80fde44d34 | 0.9429 | 0 | 0.9429 |
| pooled | 0.9781 | 3 | 0.9810 |

All three small-caps records are correct, verified against the ink rather than assumed: the E of
"MASTER", the E of "SETON", the N of "HERRING". Both failing books still fail. Filtering the
quality flags remains the only route that passes as measured, at 0.9942.

**Stop treating 0.978 as an upper bound waiting to be corrected.** The correction is applied.

**The extraction had broken every script this needed.** `gate3.py` and all five scripts in
`.gate3-recheck/` imported `pdomain_ocr_synth.pgdp`, removed on 2026-09-07. They now import
`pdomain_pgdp_measure` and must run from `/workspaces/pdomain/pdomain-pgdp-measure`. `render` now
carries `wrong` marks forward by `cell_id`, so re-rendering the sheet no longer discards review.

## The one fact that drives the new track

**No region ground truth exists anywhere in the suite, and no off-the-shelf vocabulary has the
words historical books need.** PP-DocLayout's 14 classes and DocLayNet's 11 both lack poetry,
blockquote and marginalia, and both collapse running head and folio into header and footer. The
doctr corpora are word boxes under one class. The 120-case layout regression fixture stores
PP-DocLayout's own output as its expected values, so it cannot train anything.

So the labeler is the dataset factory, not just a review tool. Everything in slices 2 to 5 exists
to produce the corpus slices 6 and 7 need.

## Three premises of the split design were wrong, and are corrected in the roadmap

Checked against code, not assumed.

- **The glyph propose-and-confirm pattern is half built.** The confirm half is real. The propose
  half is a `NoneGlyphPredictor` stub that nothing calls, and the frontend never calls
  accept-prediction.
- **The 2026-05-07 scope freeze does not bind region work**, and the `UserPageEnvelope` it guards
  is already retired. D-042 froze six infrastructure axes; region annotation is none of them. The
  owner lifted it explicitly for this track.
- **The block layer the design says nobody built is wired**, with a rail toggle, a canvas
  consumer, and a passing test.

## The vocabulary is designed and reviewed

Thirty-four roles: the twenty that ship in `Block` today unchanged, plus fourteen additions.
Structure lives on `BlockCategory`, meaning on the role, sub-word features on `word_components`.

**The governing rule is additive only. No shipped role string is renamed.** Two adversarial
reviews and a recheck established why: every rename in the first draft would have silently broken
working code. `route_sidenote_reading_order` matches the literal `"sidenote"`.
`dropcap._SKIP_ROLES` holds `"sidenote"` and `"page number"`. `figure` and `illustration` are a
live distinction between a figure carrying OCR text and an empty placeholder.

Nine findings in the first round, four in the recheck, all verified against the code.

**A real bug surfaced and is unfixed.** PP-DocLayout emits a native `page_number` label and
`PP_DOCLAYOUT_TO_PGDP` discards it into `footer`. Nothing can propose a folio automatically for
that reason alone. Fixing it needs a new `RegionType.page_number` member plus a
`_REGION_TO_BLOCK_ROLE` entry, in two repos.

## Where the design stopped

Section one, the vocabulary and the category-against-role split, is settled and written down.

Section two was presented and **the owner has not ruled on it**. Its claim: confirmed truth lives
on `Block` in the page blob, machine proposals live in a separate cached artifact, and both
persist forever, because you cannot measure the model unless you keep what it said beside what
the person decided. Rejections and edits are recorded, not just acceptances. `ReviewMetadata`
gains one field, `source`. Proposals come from a job, never from page fetch, because PP-DocLayout
is a 132 MB detector. The invariant is that the page blob is only ever written by a human action.

Sections three to five are unwritten: the routes an agent and a UI both drive, reading order with
the word-ownership invariant, and the test plan.

## Decisions the owner made this session

- Scope is slices 1, 3, 4 and 5 of the split, with model semantics included, not geometry alone.
- A full human review surface **and** an LLM able to drive all of the labeler, so a person reviews
  what the model flags at low confidence and can spot check the high-confidence pages.
- The scope freeze is lifted for this work.
- Regions are first-class `Block` objects. Not sidecars. The owner rejected the sidecar approach
  the session first recommended.
- Hierarchy is expressed by nesting, so `page header` contains `running head` and `page number`.
- A running head and a folio are never the same `LINE` block, even on one physical line of ink.
- We build our own trainer eventually. deepdoctection is a reference implementation to study, not
  a dependency to adopt.

## Open, and the owner's call

- Section two, above. It gates sections three to five.
- Whether `press figure` stays. It is real but narrow and nothing downstream asks for it.
- Whether to take the table spec's Slice A data model as a prerequisite, so the corpus carries
  cell structure from the first page rather than being relabeled later.
- Gate 3 itself: the filtered inventory, or a stated lower number.
- Re-read `e13`, `h21`, and `a10`. They are the only marks that might still be review errors.
- 490 flat-ascender words across five books, queued and unreviewed.
- The atlas policy, and M11's spec still describing NiceGUI behind a supersession banner.
- Nothing is pushed in any repository.

## Operating notes

**Run `make ci` with the venv on PATH.** Prefix `PATH="$PWD/.venv-container/bin:$PATH"`, or a
bare `git commit` fails with `pre-commit not found`.

**Commit subjects must stay within 72 characters** or gitlint rejects the commit.

**`pdomain-pgdp-measure` has no `AGENTS.md`, `CONVENTIONS.md`, or `Makefile`.** Commands run
directly through `uv`. Worth fixing before anyone implements there.

**`pdomain-ocr-labeler-spa` has an open branch** `feature/edition-companion-contract`, two commits
of tests plus a dependency bump, touching the book labeling manifest. Same area as bundle loading.

## Resume steps

1. Read `docs/plans/2026-09-07-labeling-track-roadmap.md` first. It carries all seven slices, the
   three corrected premises, and the two split-design decisions that are now answered.
2. Get the owner's ruling on design section two before writing sections three to five. The
   summary above is complete enough to re-present without redoing the analysis.
3. Then continue the `superpowers:brainstorming` architectural path: sections three, four and
   five, then the written spec, then `superpowers:writing-plans`.
4. Do not re-run the adversarial review on the vocabulary. Two rounds and a recheck are done and
   the findings are folded in.
5. For any Gate 3 work, run the scripts from `/workspaces/pdomain/pdomain-pgdp-measure`, not from
   this repository, and match glyphs on page and box rather than `line_ordinal`.

## Pointers

- Labeling track roadmap, all seven slices: `docs/plans/2026-09-07-labeling-track-roadmap.md`
- Region vocabulary, designed and reviewed: `docs/specs/2026-09-07-region-vocabulary-design.md`
- The split design this carries out: `docs/specs/2026-09-06-measurement-labeling-synthesis-split-design.md`
- Gate 3 recheck and rescore: `docs/research/2026-09-07-gate3-recheck-on-the-713-page-alignment.md`
- Roadmap, both tracks: `docs/plans/README.md`
- Current state: `docs/context/current-state.md`
- Open intent: `docs/context/intent-map.md`
- The labeler: `/workspaces/pdomain/pdomain-ocr-labeler-spa`
- Its sidecar mechanism, rejected for regions but the precedent for glyphs: `/workspaces/pdomain/pdomain-ocr-labeler-spa/src/pdomain_ocr_labeler_spa/core/labeler_sidecars.py`
- The recursive page model regions attach to: `/workspaces/pdomain/pdomain-book-tools/pdomain_book_tools/ocr/block.py`
- Drop caps, already modelled at word level: `/workspaces/pdomain/pdomain-book-tools/pdomain_book_tools/ocr/dropcap.py`
- The mapping that discards the folio signal: `/workspaces/pdomain/pdomain-book-tools/pdomain_book_tools/layout/_mappings.py`
- Table structure design, its Slice A is a candidate prerequisite: `/workspaces/pdomain/pdomain-book-tools/docs/specs/10-table-structure.md`
- The measurement package: `/workspaces/pdomain/pdomain-pgdp-measure`
- Gate 3 review sheet renderer, repointed: `/workspaces/pdomain/.m15f-evidence/gate3.py`
- Gate 3 recheck scripts, repointed: `/workspaces/pdomain/.gate3-recheck/`
- Small-caps verification crops: `/workspaces/pdomain/.gate3-recheck/small-caps-marks.png`
- The corpus: `/workspaces/pdomain-data/pgdp-corpus`
- Previous handoff: `docs/_archive/handoff/2026-09-07-102549-measurement-library-extracted-and-gate-3-recheck.md`
