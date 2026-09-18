---
kind: handoff
status: "active"
created: "2026-09-18"
created_at: "2026-09-18T01:19:30Z"
owner: CT
branch: master
scope: pgdp-synthesis
worktree: /workspaces/pdomain/pdomain-ocr-synth
base_commit: "252d8930d30238ca6ef988367379d7cd54ce60b8"
supersedes: "2026-09-17-153727-review-queue-ships-and-page-kind-review-is-being-built.md"
handoff_reason: material_resume_change
host: claude-code
---

# Slice 5 is done, and ten surfaces that lied now tell the truth

## Read this first

**Everything is merged and pushed.** `pdomain-ocr-labeler-spa` is at `195f770`,
`pdomain-ocr-synth` at `252d893`. The labeler's backend suite passes at 1880 with 4 skipped, its
frontend suite at 1944, and its browser suite at 151 passed, 12 failed, 7 skipped, where ten of
those failures predate all of this work.

**Slice 5 of the labeling track is complete** except words and glyphs in the queue. Decisions carry
across proposal runs, a book-wide queue answers what to review next, page kinds are reviewed one
page or many at a time, and a Queue drawer tab lists undecided proposals in reading or
lowest-confidence order.

**Ten issues were closed, each one a surface that claimed to do something it did not.** That
pattern is the session's main finding: the labeler had a layer of features that looked present and
were not wired to anything.

## What shipped in the labeling track

| merge | what |
| --- | --- |
| `87e4a7d` | decision carry-forward, the `regions/review-queue` route, `[` and `]`, the rail badge |
| `2adbd46` | page-kind review end to end, verified on 32 real OCR'd pages |
| `1e21990` | region proposals run on pages nobody opened, so a run works after a restart |
| `0536318` | the Queue drawer tab, with the confidence order the route already supported |

**Bottom-of-page furniture was measured and ruled out.** Marks appear on 6.6 percent of pages
against 78.6 percent for top furniture, and they sit at ordinary line spacing, so the gap rule that
finds running heads does not transfer. The evidence is in
`docs/research/2026-09-17-bottom-of-page-furniture-is-too-rare-and-too-close-to-the-text.md`.

## What shipped in the labeler's own backlog

Each of these was a feature that appeared to work. All are retired with tombstones in the labeler's
`docs/context/decisions.md`.

- **A page fetch hid OCR failures** behind an empty page and a debug line. It now says so, and
  tells a missing OCR install apart from one page's failure.
- **Canvas erase did nothing.** A page-scoped erase route now backs it, and the rail and viewport no
  longer both claim `Shift+E`.
- **Keyboard `j` and `k`** moved the worklist without moving the real selection.
- **The image drift banner could never appear**, because nothing detected drift at all.
- **Cancel** marked a job cancelled while the book kept processing, and most jobs had no Cancel
  button anywhere.
- **The jobs API and its event stream** disagreed with their own schema, so the generated types
  described a response that did not exist.
- **A cold page open** blocked for up to half a minute behind a spinner reading "Loading project".
- **Three bbox buttons** named Refine, Expand + Refine and Crop all called a plain rebox.
- **The browser suite** passed while proving nothing, because its fixture pages were one-pixel
  images and every test needing words skipped.

## What the reviews caught, and why they stay worth it

**Every branch this session came back with findings, and several were serious.** Two are worth
knowing about because they are the kind that tests do not catch:

- Moving OCR into a job dropped the protection against running OCR twice on the same page, because
  the lock that prevented it no longer covered the work.
- Making the bbox buttons real turned a fast local edit into a job that takes seconds, and the panel
  was not built for that. Four further defects followed, each found by a review round rather than by
  a test.

**Seeding the browser fixture with real words immediately exposed two product bugs**: the word match
list mounted no rows at all once a page had words, and a metrics chip stole clicks from the
page-kind button. Neither could have been caught while the fixture was blank.

## Resume steps

1. **Pick from the 14 open issues** in the labeler's `docs/issues/README.md`. The largest remaining
   is glyph annotations, `P0-GLYPH-*`, which is an unfinished feature rather than a lie. After that:
   export's dead normalize flag, the suite launcher's app shims, project-list metadata, ruff version
   skew, and the dependency refresh.
2. **Ten browser tests fail on master and did before any of this work.** They are named in the
   2026-09-18 tombstone. Nobody has triaged them; that is worth a session of its own now that the
   suite no longer hides skips.
3. **The word edit gap is filed**, `docs/issues/2026-09-18-the-word-edit-dialog-...`. It needs three
   decisions: retire the driver contract's §2.11, wire or remove the dead pencil button, and give
   word merge a home.
4. **Slice 5's remainder** is words and glyphs in the queue, and one answer to "what is next" that
   spans every kind of work rather than regions alone.

## Waiting on the owner

- **A labeler release.** The last tag is `v0.2.0` from 2026-06-06, and the commit count since is
  now well past 340. I recommend `scripts/do-release.sh` then `publish-index.sh`.
- **P2-SELECTION-PAGE:** clear every selection on page change, or carry a page index in
  `SelectionPath`.
- **Carry-forward for hand-drawn regions and for rejections.** The 2026-09-08 ruling covers neither.
- **OCR lookalike folios** such as `IO` for `10`.
- **Whether the OCR engine should warm up at server start**, which the page-load design left open.

## Operating notes

- **Reviews found something on every branch.** Budget for two rounds, and say plainly when a
  reviewer's suggestion is worth overriding rather than patching around it.
- **A subagent will sometimes use a bare `git stash`.** The stack is shared. Check
  `git stash list` after one reports; the only entry that should be there is the old
  `feature/page-kind-payload` one.
- **The browser suite takes about six minutes** and needs `make frontend-build AI=1` first. A skip
  for a reason outside `tests/e2e/conftest.py`'s allowlist now fails the run.
- **`make exercise-real` is expected to skip about a hundred tests.** The skip gate exempts it.
- **Frontend gate** from `frontend/`: `pnpm test`, `pnpm exec tsc -b --noEmit`, `lint` at 410
  warnings, `format:check`. **Backend gate** from the root: the two pytest runs and
  `basedpyright src/pdomain_ocr_labeler_spa --level error`.
- **Regenerate types after any response model change**, with `make openapi-export AI=1`, and commit
  the result.

## Parked, not forgotten

- `feature/edition-companion-contract` in the labeler is two commits ahead of master and unrelated.
- `pdomain-ops` has 68 unreleased commits and `pdomain-ocr-training` 56.
- Rotating a page whose image is a symlink outside the project fails with an unhandled error rather
  than a clean one. Only evidence scripts do that today.
- The three fields a bbox resync changes get no visual cue.
- Only `expand_only` is proven end to end in a browser; the other two refine modes need a page image
  a synthetic fixture cannot supply.
- Carried forward: 490 unreviewed flat-ascender words; the dead AppImage installer; the GPU probe
  raising when the card is full.

## Pointers

- Roadmap, slice 5: `docs/plans/2026-09-07-labeling-track-roadmap.md`
- Page-kind review design: `docs/specs/2026-09-17-page-kind-review-design.md`
- Book review queue design: `docs/specs/2026-09-17-book-review-queue-design.md`
- Bottom furniture research: `docs/research/2026-09-17-bottom-of-page-furniture-is-too-rare-and-too-close-to-the-text.md`
- Labeler current state: `/workspaces/pdomain/pdomain-ocr-labeler-spa/docs/context/current-state.md`
- Labeler tombstones, where every retired issue's reasoning lives:
  `/workspaces/pdomain/pdomain-ocr-labeler-spa/docs/context/decisions.md`
- Real-book evidence: `/workspaces/pdomain/.m15f-evidence/real-book-page-kind-review/README.md`
- Previous handoff: the file named in this document's `supersedes` frontmatter
