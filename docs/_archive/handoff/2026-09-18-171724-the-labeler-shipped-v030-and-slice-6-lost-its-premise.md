---
kind: archive
status: retired
created_at: "2026-09-18T17:17:24Z"
owner: "CT"
branch: "master"
scope: "pgdp-synthesis"
worktree: "/workspaces/pdomain/pdomain-ocr-synth"
base_commit: "e718ef8e704fb9a9cf03eed023da7f379fca9be4"
supersedes: "2026-09-18-110548-slice-5-is-complete-and-everything-open-needs-a-decision.md"
handoff_reason: "material_resume_change"
host: "claude-code"
created: "2026-09-18"
last_verified: "2026-09-19"
---

> **Retired — superseded by `docs/handoff/2026-09-19-005040-five-releases-and-the-labeler-backlog-is-empty.md`.**


# The labeler shipped v0.3.0, and slice 6 lost its premise

## Read this first

**The labeler has no open issues.** Seventeen this morning, none now. Every one
was either fixed or retired with its reasoning recorded in
`pdomain-ocr-labeler-spa/docs/context/decisions.md`.

**Four releases went out**, the first in three months. The labeler at `v0.3.0`
after 561 commits, `pdomain-ops` at `v0.12.0`, `pdomain-ocr-training` at
`v0.3.0`, `pdomain-ocr-synth` at `v0.1.0`. The pip index is regenerated, so all
four are installable.

**Every gate is green and was verified, not reported.** `make ci` passes in the
labeler, ops, training, synth, book-contracts and pgdp-measure. The labeler's
browser suite is 171 passed, 0 failed, for the first time; it had carried two
known failures for months.

## Slice 6 is blocked on its own premise, and the premise failed

The roadmap deferred poetry against blockquote to a vision-language model
because geometry supposedly cannot separate them. Nobody had ever measured
that.

**Measured on 2026-09-18** over the same five aligned books as the furniture
note, cross-checked against the PGDP F2 round's own `/* poetry */` and
`/# blockquote #/` markup:
`docs/research/2026-09-18-ragged-right-finds-poetry-blockquote-has-no-geometric-signature.md`.

- Poetry separates on **raggedness**, 87.5 percent precision and 93.3 recall,
  stable across a sevenfold threshold range. The indent the roadmap named is a
  smear, because verse lines fall short of the measure and so read as indented
  on both sides. That is why the two rules as written collide on 834 blocks.
- **A one-line text rule beats every geometric signal**: whether each line
  starts with a capital, 95.4 percent precision. No model is needed.
- **Blockquote is unknown, not disproved.** Best rule reached 2.3 percent
  precision, but ground truth is 44 heterogeneous spans across the corpus.

Read the caveat before quoting the numbers: one book is a poetry anthology and
carries the pooled figures. The other four hold 22 confirmed poetry blocks
between them.

**The most useful finding is about evidence, not poetry.** A survey the same
day concluded no region ground truth exists anywhere. It was wrong. PGDP's own
formatting markup is ground truth, already in the corpus, matching measured ink
bands on 801 of 1,193 usable pages. Future role claims can be measured instead
of assumed.

## The pattern that produced most of today's work

**Surfaces that looked like they worked.** Each fix exposed the next:

- The per-word validate button gated on page-wide review completion, which
  itself required every word already validated. Fixing it made the button
  depend on a typography endpoint, which exposed that a word's identity was
  computed from OCR text in one place and live ground-truth text in another, so
  correcting a word 404'd its own review forever. Fixing that exposed that a
  correction was bound to a whole-page hash, so correcting one word invalidated
  every other word's review on the page.
- Three dead affordances in one component tree. Clicking a line card did
  nothing; the Matches pane's Validate, Delete and both copy buttons were never
  wired; and a ground-truth edit typed into that pane was silently discarded.
- Per-word sidecars did not follow their words through eleven structural
  routes, so hand-drawn character boxes and glyph marks moved onto neighbours.
  Nothing errored, which is why it survived.

**Tests hid most of it.** Three separate tests asserted almost nothing while
passing. One clicked a card, pressed two hotkeys that were swallowed by a text
input, fired zero requests, typed a literal `v` into the ground truth, and
passed because all it checked was that the page shell still existed.

## Operating notes that earned their place

- **Measure before designing a count or a claim.** Four times now. Project
  progress, the typography numerator, word validation state, and slice 6's
  premise all turned out different from the assumption.
- **Write the count where the data is already written.** The per-page counts
  journal made words, typography and project progress affordable at all.
- **Ask the implementer to say when the instruction is wrong.** It happened
  five times today and each was an improvement: line merge re-sorts rather than
  appends so no offset formula works; word merge already had a home in the
  right panel; bounding boxes had to leave the typography hash too; three
  carried-forward items belonged to other repos; and the CI issues were moot
  because the workflows were deleted.
- **A subagent that starts a background task and stops never gets its result.**
  Four agents lost time this way. Tell them to block in the foreground.
- **A green suite proves less than it looks.** Two fixes today were only found
  because a full-suite run failed where a single-file run passed.

## Resume steps

1. **Poetry is implementable now, and it is not slice 6 work.** Raggedness plus
   line-initial capitals belongs in the geometry track beside the furniture
   rules, as a `propose_regions` detector. It would also produce the first
   `region-decisions.jsonl` this system has ever had, which is what every
   future role claim needs.
2. **Slice 6 needs a new justification.** Its standard example does not survive
   measurement, and nobody has named a replacement case.
3. **Blockquote needs ground truth before anything else.** 44 spans is not
   enough to design against.

## Waiting on the owner

- Carry-forward for hand-drawn regions and for rejections.
- OCR lookalike folios, such as `IO` for `10`.
- Whether the OCR engine should warm up at server start.
- Whether the two adjacent accordion items named Glyphs and Typography read
  well to a person reviewing a word. Cosmetic, no defect behind it.

## Parked, not forgotten

- `feature/edition-companion-contract` in the labeler is two commits ahead of
  master and unrelated.
- `set_region_word_membership` can renumber every line on a page; known, owned
  elsewhere, pinned by its own test.
- A word's own bbox nudge no longer stales its own typography review, because
  the upstream contract leaves no per-word slot to carry box currency.
- Word and typography counts for a multi-page bundle book report unavailable.
- A project list of 200 with journals at their pre-compaction ceiling costs
  about seven seconds; the number to look at first if the list feels slow.
- Reported upstream and unfixed: `pdomain-book-tools`' `merge_adjacent_words`
  clears ground truth for every word in the line, not the merged pair.

## Pointers

- Labeler decisions, where every retired issue's reasoning lives:
  `/workspaces/pdomain/pdomain-ocr-labeler-spa/docs/context/decisions.md`
- Labeler current state:
  `/workspaces/pdomain/pdomain-ocr-labeler-spa/docs/context/current-state.md`
- The poetry measurement:
  `docs/research/2026-09-18-ragged-right-finds-poetry-blockquote-has-no-geometric-signature.md`
- Roadmap, with slice 6 held:
  `docs/plans/2026-09-07-labeling-track-roadmap.md`
- Previous handoff: the file named in this document's `supersedes` frontmatter
