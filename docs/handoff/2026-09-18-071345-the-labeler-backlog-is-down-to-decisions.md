---
kind: handoff
status: "active"
created: "2026-09-18"
created_at: "2026-09-18T07:13:46Z"
owner: CT
branch: master
scope: pgdp-synthesis
worktree: /workspaces/pdomain/pdomain-ocr-synth
base_commit: "5584165a7e100e4b3c893a6e1ced9c64886c9287"
supersedes: "2026-09-18-011928-slice-5-complete-and-ten-product-honesty-bugs-closed.md"
handoff_reason: material_resume_change
host: claude-code
---

# What is left in the labeler needs a decision, not more code

## Read this first

**The labeler's issue backlog is down to six reports, and every one of them is
waiting on a person.** Seventeen were closed since yesterday morning. What
remains is not blocked on effort; it is blocked on somebody saying what the
product should do.

**Everything is merged and pushed.** `pdomain-ocr-labeler-spa` is at `a9a90fb`,
`pdomain-ocr-synth` at `5584165`. The labeler's backend suite passes at 1908
with 4 skipped, its frontend at 2036, and its browser suite at 160 passed, 2
failed, 7 skipped, both failures owned by open issues.

**Glyph review works now.** Mark a word's ligatures, long s or swash, or mark it
reviewed with no marks, and the mark reaches the server, comes back on the next
read, and survives a reload. Before this, a bulk apply did not merely fail to
save: it raised on the page id and failed outright for everyone.

## The six decisions

Each has a filed issue with evidence and a recommendation.

1. **Glyph predictions do not exist.** `IGlyphPredictor` is unwired, so the
   accept button cannot fire for anyone. Everything around it is built. Task 10
   of the glyph plan.
2. **The per-word validate button can never validate a word.** Review completion
   requires every word validated, and the button is disabled until review is
   complete. It only works as a one-shot unvalidate. My recommendation: gate it
   on that word's own typography review rather than the whole page's.
3. **The word edit dialog is documented and absent.** A dead pencil button, 18
   advertised shortcuts that do nothing, and word merge with nowhere to live.
4. **Text normalization waits on a module that has never existed.** A route, a
   probe and a page-text call all report the feature as one upgrade away. A real
   normalizer exists and does something else: curly quotes and em dashes, not
   long s and ligatures.
5. **Selection on page change**, the older P2-SELECTION-PAGE question.
6. **Archive semantics**, which is the only thing standing between the project
   list and a working status filter.

## What shipped since the last handoff

| merge | what |
| --- | --- |
| `199aa66` | the browser suite's twelve failures, triaged: eight stale tests, five dead hotkeys, one off-screen dialog |
| `c68661d` | the export request's dead normalize flag, removed rather than faked |
| `df005c0` | the suite launcher, which showed nothing because its stubs reported nothing and its slot was never mounted |
| `3200aa7` | real page counts on project cards, and three inert filter chips removed |
| `0f8f20b` | glyph marks persist, and bulk apply works at all |
| `c0cbf76` | the glyph panel mounted, with its hooks and a browser test |

Five hotkeys the app advertised were dead, two of them since a dependency bump
that started matching physical key positions, one silently split in half by the
library's own comma delimiter. The hotkey help dialog rendered entirely
off-screen, because it carried both the shared dialog transform and Tailwind
translate classes, which compose rather than override.

## The pattern worth carrying forward

**Every fix exposed the next one.** A dead shortcut hid a broken dialog. Blank
test fixtures hid a list that rendered no rows at all. A test suite that skipped
instead of failing hid both. Stubs that reported nothing hid a launcher that was
never mounted.

**Reviews found something on every branch, and several were serious**: a lost
guard against running OCR twice on the same page, a server path leaked to the
browser, a page count that would have read zero for every book project, a
duplicate-write guard that was exported and never consumed. Budget for two
rounds per branch.

**Prefer removing a dead control to building a feature that justifies it.** The
export flag went; the filter chips went. Both left the product more honest than
a half-built capability would have.

## Resume steps

1. **Take a decision from the list above**, or ask the owner. Nothing else in
   the labeler is unblocked.
2. **Two browser tests fail**, both owned: the word edit dialog one, and
   `test_validate_and_save_keyboard_only`, which passes alone and fails only
   under load here.
3. **The labeling track's slice 5 is complete** apart from words and glyphs in
   the review queue, and one answer to "what is next" spanning every kind of
   work rather than regions alone. That is the next substantial build if you
   would rather write code than decide.

## Waiting on the owner, beyond the six

- **A labeler release.** The last tag is `v0.2.0` from 2026-06-06, and the
  commit count since is well past 400 now. `scripts/do-release.sh` then
  `publish-index.sh`.
- **Carry-forward for hand-drawn regions and for rejections.**
- **OCR lookalike folios**, such as `IO` for `10`.
- **Whether the OCR engine should warm up at server start.**

## Operating notes

- **The browser suite takes about four minutes** and needs `make frontend-build
  AI=1` first. A skip for a reason outside `tests/e2e/conftest.py`'s allowlist
  fails the run.
- **Frontend gate** from `frontend/`: `pnpm test`, `pnpm exec tsc -b --noEmit`,
  `lint` at 400 warnings now, down from 410, `format:check`. **Backend gate**:
  the two pytest runs and `basedpyright src/pdomain_ocr_labeler_spa --level
  error`.
- **Regenerate types after any response model change** with `make openapi-export
  AI=1`, and commit the result.
- **A subagent will sometimes reach for `git stash`.** The stack is shared.
  Check `git stash list` after one reports; the only entry that should be there
  is the old `feature/page-kind-payload` one.
- **Ask an implementer to say when a reviewer's suggestion is wrong.** Twice
  today that produced a better design than the one I asked for: a per-field
  resync instead of disabled inputs, and a shrinkable toolbar control instead of
  a fixed width cap.

## Parked, not forgotten

- `feature/edition-companion-contract` in the labeler is two commits ahead of
  master and unrelated.
- `pdomain-ops` has 68 unreleased commits and `pdomain-ocr-training` 56.
- Progress on project cards needs a save-time cache; `write_project_json` and
  `Project.saved_pages` exist for it and nothing calls them.
- Two adjacent accordion items now read Glyphs and Typography. Whether that is
  coherent to a person reviewing a word is worth a look.
- Rotating a page whose image is a symlink outside the project fails with an
  unhandled error.
- Carried forward: 490 unreviewed flat-ascender words; the dead AppImage
  installer; the GPU probe raising when the card is full.

## Pointers

- Labeler issues, all six: `/workspaces/pdomain/pdomain-ocr-labeler-spa/docs/issues/README.md`
- Labeler tombstones, where every retired issue's reasoning lives:
  `/workspaces/pdomain/pdomain-ocr-labeler-spa/docs/context/decisions.md`
- Labeler current state: `/workspaces/pdomain/pdomain-ocr-labeler-spa/docs/context/current-state.md`
- Glyph plan, with its remaining tasks:
  `/workspaces/pdomain/pdomain-ocr-labeler-spa/docs/plans/2026-07-21-glyph-annotations-completion.md`
- Roadmap, slice 5: `docs/plans/2026-09-07-labeling-track-roadmap.md`
- Previous handoff: the file named in this document's `supersedes` frontmatter
