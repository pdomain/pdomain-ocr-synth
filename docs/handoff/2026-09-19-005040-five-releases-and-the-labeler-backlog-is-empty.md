---
kind: handoff
status: "active"
created: "2026-09-19"
created_at: "2026-09-19T00:50:40Z"
owner: CT
branch: master
scope: pgdp-synthesis
worktree: /workspaces/pdomain/pdomain-ocr-synth
base_commit: "a58142262716e0f986e7d668b247e8fe557b3435"
supersedes: "2026-09-18-171724-the-labeler-shipped-v030-and-slice-6-lost-its-premise.md"
handoff_reason: material_resume_change
host: claude-code
---

# Five releases, and the labeler has nothing open

## Read this first

**The labeler has no open issues and no open findings.** Seventeen issues and
six findings were closed. Every one is recorded with its reasoning in
`pdomain-ocr-labeler-spa/docs/context/decisions.md`.

**Six releases went out**, the first in three months:

| repo | version | note |
| --- | --- | --- |
| `pdomain-ocr-labeler-spa` | `v0.5.0` | 587 commits past `v0.2.0` |
| `pdomain-ui` | `v0.13.0` | a job can be cancelled |
| `pdomain-book-tools` | `v0.29.0` | word merge stops eating ground truth |
| `pdomain-ops` | `v0.12.0` | |
| `pdomain-ocr-training` | `v0.3.0` | |
| `pdomain-ocr-synth` | `v0.1.0` | 311 commits past `v0.0.2` |

Both indexes are regenerated, so all six install.

**Every gate is green and was run, not reported.** The labeler's `make ci`
passes, its browser suite is 180 passed with 0 failed, and `pdomain-book-tools`
and the rest pass their own.

## Slice 6 is still held, and the reason has not changed

Its premise failed measurement on 2026-09-18:
`docs/research/2026-09-18-ragged-right-finds-poetry-blockquote-has-no-geometric-signature.md`.
Poetry separates on raggedness at 87.5 percent precision, and a rule checking
whether each line starts with a capital reaches 95.4. **No model is needed to
find poetry**, so the slice lost its standard example and nobody has named a
replacement case.

That detector now ships in the labeler, in `core/regions/poetry.py`. Its
confidence is the measured precision of whichever rule decided, documented as
pooled rather than calibrated, because the corpus figure leans on one book that
is a poetry anthology.

**Blockquote is the honest unknown**: best rule 2.3 percent precision over 44
heterogeneous ground-truth spans. That is the corpus failing to answer, not a
measured no.

**The most useful finding was about evidence.** PGDP's own `/* poetry */` and
`/# blockquote #/` formatting markup is region-role ground truth, already in
the corpus, matching measured ink bands on 801 of 1,193 usable pages. A survey
the same day had concluded no such ground truth existed anywhere. It was wrong.

## The pattern that produced nearly all of it

**Surfaces that looked like they worked.** Each fix exposed the next, and the
chain ran for a full day:

- The per-word validate button gated on page-wide completion, which required
  every word already validated. Fixing it made the button depend on a
  typography endpoint, which exposed that a word's identity was computed from
  OCR text in one place and live ground truth in another, so correcting a word
  404'd its own review forever. Fixing that exposed a correction bound to a
  whole-page hash, so correcting one word invalidated every other word's review
  on the page.
- Per-word sidecars did not follow their words through **eleven** structural
  routes, so hand-drawn character boxes and glyph marks moved onto neighbours.
  Nothing errored, which is why it survived.
- A page where OCR found nothing looked finished, and the review queue agreed,
  reporting zero outstanding because zero words minus zero validated is zero.
- Three dead affordances in one component tree, including a ground-truth edit
  that was silently discarded on blur.

**Tests hid most of it, and one lesson generalised.** A test that documents a
workaround for product behaviour is a bug report nobody filed. Acting on that
found the SSE handler losing a fast job's terminal event and hanging the stream
forever, described in a docstring since May. A sweep for the same pattern then
found a page response that could contradict itself, reading its counts under a
lock and its history outside one.

## Operating notes that earned their place

- **Measure before designing.** Five times now: project progress, the
  typography numerator, word validation state, slice 6's premise, and the
  folio lookalike substitutions, which came from a real run's evidence rather
  than a guessed list.
- **Check a finding against the code before building to it.** Of 24 open issues
  in `pdomain-book-tools`, 11 are real, 3 stale and 10 not defects. Two of the
  labeler's six findings were stale the same way, already answered by work
  nobody linked back.
- **Ask the implementer to say when the instruction is wrong.** It happened
  eight times and every one was an improvement, including: line merge re-sorts
  rather than appends so no offset formula works; bounding boxes had to leave
  the typography hash too; the config directory does hold user data, contrary
  to the finding that said it did not; and a panel nested where it read well on
  paper was unreachable on exactly the page it existed for.
- **A subagent that starts a background task and stops never gets its result.**
  Six lost time this way. Tell them to block in the foreground.
- **A race test that cannot fail on most of its samples is not a race test.**
  One agent noticed its own first attempt passed by luck and rewrote it.
- **Do not run git in a shared checkout an agent is using.** A branch operation
  landed an agent's commit on `master`; it recovered via reflog, but use a
  worktree.

## Resume steps

1. **`pdomain-book-tools` has the largest real backlog**, 11 issues, triaged
   with evidence. Two are in flight. The next in rank are the layout registry
   rejecting detector kwargs, so air-gapped callers cannot pass a checkpoint,
   and captions printed above a plate never being associated.
2. **Slice 6 needs a new justification**, or the track moves to slice 7.
3. **The first `region-decisions.jsonl` has still never been written.** The
   poetry detector makes it possible. Nothing has ever reviewed a region
   proposal, so there is no evidence anywhere about where role detection fails.

## Waiting on the owner

- Whether two adjacent accordion items named Glyphs and Typography read well.
  Cosmetic, no defect behind it.
- `pdomain-book-tools` has six `dep-refresh` pull requests open since
  2026-08-09 with no automated path to land, now that its workflows are gone.

## Parked, not forgotten

- `feature/edition-companion-contract` in the labeler is unrelated and behind.
- `set_region_word_membership` can renumber every line on a page; owned
  elsewhere, pinned by its own test.
- A word's own bbox nudge no longer stales its own typography review, because
  the upstream contract leaves no per-word slot for box currency.
- The labeler parses doctr's log output to guess OCR progress, because there is
  no callback. A downstream repo depending on log text as an undeclared API.
- Word and typography counts for a multi-page bundle book report unavailable.
- Nothing shows a carried region rejection outside the panel built for it.

## Pointers

- Labeler decisions, where every retired issue's reasoning lives:
  `/workspaces/pdomain/pdomain-ocr-labeler-spa/docs/context/decisions.md`
- Labeler current state:
  `/workspaces/pdomain/pdomain-ocr-labeler-spa/docs/context/current-state.md`
- The poetry measurement:
  `docs/research/2026-09-18-ragged-right-finds-poetry-blockquote-has-no-geometric-signature.md`
- Roadmap, slice 6 held:
  `docs/plans/2026-09-07-labeling-track-roadmap.md`
- Previous handoff: the file named in this document's `supersedes` frontmatter
