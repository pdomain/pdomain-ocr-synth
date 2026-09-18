---
kind: handoff
status: "active"
created: "2026-09-18"
created_at: "2026-09-18T11:05:49Z"
owner: CT
branch: master
scope: pgdp-synthesis
worktree: /workspaces/pdomain/pdomain-ocr-synth
base_commit: "10af84e034c5d1d4effc529d168e5cad133e7106"
supersedes: "2026-09-18-071345-the-labeler-backlog-is-down-to-decisions.md"
handoff_reason: material_resume_change
host: claude-code
---

# Slice 5 is complete, and everything still open needs a decision

## Read this first

**A person now gets one answer to what to review next.**
`GET .../review-queue` reports every kind of review work in the order the work
has to happen: page kinds, regions, words, typography, glyphs. The rail badge
names the first kind with work, the Queue tab picks a kind, and `[` and `]`
follow it.

**Everything is merged and pushed.** `pdomain-ocr-labeler-spa` is at `10fdcb4`,
`pdomain-ocr-synth` at `10af84e`. The labeler's backend suite passes at 1946
with 4 skipped, its frontend at 2072, and its browser suite at 163 passed, 2
failed, 7 skipped, both failures owned by open issues.

**Nothing in the labeler is blocked on effort.** Seven issues remain and every
one waits on somebody deciding what the product should do.

## What slice 5 needed, and what it cost

Counting was the whole problem. Regions and page kinds were already cheap,
because a person's decision lands in a journal that can be read without opening
a page: 0.41 ms and 0.74 ms. Words were not. Whether a word still needs a person
is a label inside the page's content blob, so counting a 300-page book meant
parsing every page, about 14 seconds.

**So one function now writes a per-page count where a page is already saved.**
`save_page_content_to_store` appends to `.pd-pages/word-review-counts.jsonl`
after the head is durably saved, for 0.20 ms, which is free against the work
already happening there. That one journal made words and typography countable at
all.

**Three kinds cannot always answer, and say so instead of reporting zero.**
Glyphs have no predictor, confirmed on 18,463 real words. A typography
corrections journal past 512 KiB costs too much to read per request, measured at
about 80 microseconds a row, 1.5 s at full coverage. A multi-page bundle book
cannot give a word denominator without opening every page.

## The decisions waiting for you

Each has a filed issue with evidence and a recommendation. In the order I would
take them:

1. **The per-word validate button can never validate a word.** Review completion
   requires every word validated, and the button is disabled until review is
   complete. It only works as a one-shot unvalidate. Recommendation: gate it on
   that word's own typography review.
2. **Glyph predictions do not exist.** `IGlyphPredictor` is unwired, so the
   accept button cannot fire for anyone. Everything around it is built and
   tested.
3. **The typography numerator needs a per-page rollup**, written where a
   correction is accepted, the same shape as the word counts journal. That
   removes the 512 KiB ceiling and is a precondition for ever affording the
   staleness check the route skips.
4. **The word edit dialog is documented and absent.** A dead pencil button, 18
   advertised shortcuts that do nothing, and word merge with nowhere to live.
5. **Text normalization waits on a module that has never existed.**
6. **Selection on page change**, the older P2-SELECTION-PAGE question.
7. **Archive semantics**, the last thing between the project list and a working
   status filter.

## What shipped since the last handoff

| merge | what |
| --- | --- |
| `f175297` | the counts journal and `GET .../review-queue`, answering for every kind |
| `0451f98` | the SPA following it: badge, kind selector, bracket keys |

Three things were found while building it, each of which would have made the
queue lie. Undo, redo and a fresh OCR ingest all write a page's content without
going through the save function, leaving a stale count that overstated
completion. Bundle projects validate text through a different journal entirely,
so they would have reported zero outstanding forever. And nothing invalidated
the new query after a decision, so the badge went stale until an unrelated
remount.

## Resume steps

1. **Take a decision from the list above**, or ask the owner.
2. **Slice 6, model-proposed semantics**, is the next substantial build in the
   track. It needs its own design first, and no LLM or VLM code exists anywhere
   in the workspace yet. The synthesis design's ruling stands: model output is
   never treated as verified ground truth.
3. **Two browser tests fail**, both owned: the word edit dialog one, and
   `test_validate_and_save_keyboard_only`, which passes alone and fails only
   under load here.

## Waiting on the owner, beyond the seven

- **A labeler release.** The last tag is `v0.2.0` from 2026-06-06, with well
  past 400 commits since. `scripts/do-release.sh` then `publish-index.sh`.
- **Carry-forward for hand-drawn regions and for rejections.**
- **OCR lookalike folios**, such as `IO` for `10`.
- **Whether the OCR engine should warm up at server start.**

## Operating notes

- **Measure before designing a count.** Three times now a design assumed
  something was cheap and measurement said otherwise: project progress, the
  typography numerator, and the word validation state. The pattern that works is
  to write the count where the data is already being written.
- **Reviews found something on every branch this session**, several serious.
  Budget two rounds.
- **Ask an implementer to say when a reviewer's suggestion is wrong.** Three
  times that produced a better design than the one I asked for, including
  dropping a panel heading rather than renaming it, and a per-field resync
  instead of disabled inputs.
- **The browser suite takes about four minutes** and needs `make frontend-build
  AI=1` first. A skip outside `tests/e2e/conftest.py`'s allowlist fails the run.
- **Frontend gate** from `frontend/`: `pnpm test`, `pnpm exec tsc -b --noEmit`,
  `lint` at 400 warnings, `format:check`. **Backend gate**: the two pytest runs
  and `basedpyright src/pdomain_ocr_labeler_spa --level error`.

## Parked, not forgotten

- `feature/edition-companion-contract` in the labeler is two commits ahead of
  master and unrelated.
- `pdomain-ops` has 68 unreleased commits and `pdomain-ocr-training` 56.
- Word and typography counts for a multi-page bundle book report unavailable;
  making them countable needs a per-page word total the manifest does not carry.
- Progress on project cards needs a save-time cache; `write_project_json` and
  `Project.saved_pages` exist for it and nothing calls them.
- Two adjacent accordion items now read Glyphs and Typography.
- Carried forward: 490 unreviewed flat-ascender words; the dead AppImage
  installer; the GPU probe raising when the card is full.

## Pointers

- The queue design: `docs/specs/2026-09-18-one-answer-to-what-to-review-next.md`
- Roadmap, slice 5 complete: `docs/plans/2026-09-07-labeling-track-roadmap.md`
- Labeler issues, all seven: `/workspaces/pdomain/pdomain-ocr-labeler-spa/docs/issues/README.md`
- Labeler tombstones, where every retired issue's reasoning lives:
  `/workspaces/pdomain/pdomain-ocr-labeler-spa/docs/context/decisions.md`
- Labeler current state: `/workspaces/pdomain/pdomain-ocr-labeler-spa/docs/context/current-state.md`
- Previous handoff: the file named in this document's `supersedes` frontmatter
