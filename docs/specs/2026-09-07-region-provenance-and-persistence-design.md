# Region provenance and persistence

## Agent Index

- **Kind:** spec
- **Status:** draft
- **Owner:** CT
- **Created:** 2026-09-07
- **Last verified:** 2026-09-07
- **Provenance:** designed 2026-09-07 with the owner, from direct inspection of
  `pdomain-pgdp-measure/page_templates.py`, `pdomain-prep-for-pgdp/core/models.py`,
  `core/auto_detect.py`, `core/pipeline/stage_registry.py`, `api/data/project_stages.py`,
  `pdomain-ocr-labeler-spa/core/glyph/predictions.py`, `core/labeler_sidecars.py`,
  `core/page_state.py`, `core/jobs/runner.py`, `api/jobs.py`, `api/words.py`,
  `core/persistence/page_store.py`, `core/persistence/book_labeling_manifest.py`,
  `pdomain-book-tools/ocr/block.py`, `ocr/page.py`, `ocr/word.py` and
  `ocr/ground_truth_matching.py`, and
  `pdomain-book-contracts/ocr/glyph_annotations.py` and `ocr/review.py`
- **Disposition:** Draft. Section two of the slice 1 and 2 design. The routes, reading order, and
  test plan are still unwritten. No code has moved.
- **Read when:** deciding where a region, word, or page-kind annotation is stored, how a machine
  proposal is kept beside a human decision, how page kind is classified, or how the execution
  engine reads regions without a human in the loop.
- **Search terms:** region provenance, proposal set, decision log, page blob invariant, page kind,
  PageClass, PageType, confidence threshold, resolved regions, propose and confirm, ground truth
  provenance, ReviewMetadata source, ocr_confidence.

**Plan:** [Labeling track roadmap](../plans/2026-09-07-labeling-track-roadmap.md), slices 1 and 2.

**Spec:** [Region vocabulary](2026-09-07-region-vocabulary-design.md) is section one. This is
section two.

## What this settles

Machine proposals and human decisions live in separate stores that both persist. A single read
path resolves them into the regions a caller sees. Confirmed regions are `Block` objects in the
page blob. Proposals are per-run artifacts that are never edited. A third small store records what
a person decided about each proposal.

The same treatment applies to OCR words and to page kind, at different cost. Words already store
the machine's claim and the human's answer separately and need only provenance added.

The reason is measurement. You cannot score a model unless you keep what it said beside what the
person chose. Two shipped features in the suite overwrite one with the other and so cannot be
scored. The word model is the exception, and it is the pattern to follow.

## Storing one set loses the model's claim, and two shipped features prove it

The glyph annotations in the labeler use one object with a `source` field that moves through
`human`, `predicted`, and `human_confirmed`. Accepting a prediction copies it into the confirmed
map with the source rewritten. The prediction itself is never written to the content blob at
all. It lives only on in-memory page state, so it dies with the request.

Rejection leaves no trace whatever, because there is no reject route. The accept endpoint exists
and its counterpart does not. So a person who disagrees with a prediction simply edits past it, and
the disagreement is never recorded.

The prep app loses the same information a second way. Its route that persists a user-edited zone
layout writes over the canonical artifact path. The detector's own output is not kept beside the
edit.

Both features work. Neither can answer how often its model was right, which is the question the
labeling track exists to answer.

## Three stores, and what each one holds

**Proposals** hold what a machine said. One immutable record per run per page, carrying the model
identity and version, the proposed geometry and role, a confidence value, and the evidence behind
it. Nothing edits a proposal after it is written.

**Confirmed regions** hold what a person decided. These are `Block` objects in the page blob, and
they are the ground truth the trainer reads.

This overrides the roadmap, which rejected `Block` and chose a `regions_map` sidecar beside
`glyph_annotations_map`. The owner ruled on 2026-09-07 that regions are first-class `Block`
objects, not sidecars. The roadmap's two open decisions section has been updated to match.

The roadmap's technical objection was that the labeler never touches `Block`. That is true of
imports today and is a cost, not a blocker.

Its implied worry about losing data does not hold: `block_role_labels` is written by
`Block.to_dict` and read back by `from_dict`, so role labels round-trip cleanly. The attribute that
is genuinely lost on that round trip is the line-level validated flag, which is a separate concern.

**Decisions** join the two. One record per proposal, naming the run, the disposition, and the
confirmed region it produced. The disposition is accepted, edited, or rejected.

The third store exists because absence is ambiguous. If only the confirmed regions carried a link,
a rejected proposal would have no counterpart. Nothing would then separate "a person looked at this
and said no" from "nobody has looked yet". Those are opposite facts, and a trainer needs both.

## The same three stores apply to OCR words, and two of them already exist

Words get this treatment too, by owner direction on 2026-09-07. The work there is smaller than for
regions, because the storage is already right.

`Word` keeps the machine's claim and the human's answer side by side. `text` and `ocr_confidence`
hold what the recognizer said. `_ground_truth_text` holds the answer. `review` is `None` until a
review pass touches the word, so the unreviewed state is already distinct from the reviewed one.
Correcting a word does not destroy what the OCR read.

What is missing is provenance on the answer. Four different writers fill `ground_truth_text` and
nothing records which one did:

| writer | what it is |
| --- | --- |
| `ground_truth_matching.py:353` | F2 alignment, a machine |
| `api/words.py:555` | a person typing in the labeler |
| `api/lines_paragraphs.py:951-955` | split and merge redistributing tokens |
| `jobs/handlers/export.py:204` | copies `word.text` into the field wholesale |

So machine text lands in the ground-truth field with no marker separating it from a human's answer.
The last row is the sharpest case: an export stamps the OCR's own output in as ground truth.

This matters beyond bookkeeping. F2 alignment is best effort and neither side of it is ground
truth, so a trainer that reads `ground_truth_text` without knowing its origin cannot tell a
confirmed reading from an alignment guess.

The fix is the `source` field this design puts on `ReviewMetadata`, applied at word level. No new
store is needed.

## When a decision store is required, and when a marker is enough

The three cases in this design need different amounts of machinery, and one rule explains why.

**A decision store is required only when the human's answer is sparse against the machine's
output.** A page holds many regions and a person may confirm some and ignore the rest, so absence
stays ambiguous and each proposal needs its own recorded disposition.

**Otherwise a diff plus a reviewed marker is enough.** A word has one answer and a page has one
kind, so the human's answer replaces the machine's whole. Comparing the two tells you whether it
was accepted or changed, and the marker tells you somebody looked.

So regions get all three stores. Words and page kind get two stores and a marker.

## A region is identified by its geometry, never by its position in a list

The sidecar maps that already ship key their entries by position, as a `line_index` and
`word_index` joined by an underscore. Regions must not copy that.

Line numbering is not stable. The band-identification fixes renumber lines, and an earlier analysis
in this repository was invalidated when it matched glyphs on line ordinal across a renumbering. A
positional key silently reattaches an annotation to a different piece of ink.

So a region carries a stable identifier of its own, and a proposal references that identifier. Any
matching between a proposal and a confirmed region is done on page and box, not on ordinal.

## The page blob is only ever written by a human action

This invariant is what keeps the three stores honest. A proposal job may write proposals. It may
never write the page blob. A person's confirmation is the only thing that does.

The prep app already states the same rule for its own suggestions: they "land on the page record
only after the user confirms them in the page tagger", and the auto-detect step "never silently
mutates state".

## A proposal run records what it was conditioned on

Region proposals depend on page kind, so a region proposal is only as good as the page kind it
assumed. A run therefore stores its inputs alongside its outputs: the model version, and the
page-kind decision it read, including whether that decision was human-confirmed or itself a
proposal.

Without this, relabeling a page kind silently invalidates every region proposal derived from it.
No evaluation number can then be traced to the thing that produced it.

The anchor for a run is already available. The labeler stores page content as a blob keyed by its
SHA-256 digest. The page aggregate records that digest in its provenance chain. A run names the
exact content hash it read, so a proposal can always be tied to the page state that produced it.

## The job machinery a proposal run needs already exists

The labeler runs an in-process asyncio job runner with a queued, running, and terminal lifecycle.
It exposes list, fetch, cancel, and a server-sent event stream whose first frame is a snapshot,
which is the kick-off-and-poll shape a proposal run needs. Reload OCR, rotate, auto-rotate, refine,
export, and save-project already run through it.

One property constrains the design: job rows live in memory and are lost on restart. A proposal run
must therefore write its output to durable storage as it goes. It should treat the job row as
progress reporting, not as the record.

One write path is also a trap worth naming. Saving a page to the store fires an edit event carrying
only a changelog diff. It does not re-serialize the page, and the code itself flags this as its top
audit finding. The function that writes page content addressably is the one anything storing
regions must call.

## One read path serves both the labeler and the execution engine

Callers never read the three stores directly. They ask for a page's resolved regions, and the
resolver returns the confirmed region where one exists, otherwise the best proposal above a
confidence threshold, otherwise nothing.

The labeler calls it with the threshold at zero and renders proposals visibly distinct from
confirmed regions. The execution engine calls it with a real threshold and treats the result as the
answer. One function, two callers, and no second pipeline to keep in step.

This is what lets the execution engine run all three passes with no human. In production, the
confirmed store and the decision store are simply empty, so the resolver falls through to proposals
every time. The page blob invariant still holds, because no human acts and so nothing writes it. The
prep app already carries the threshold this needs, as `layout_detector_confidence`, defaulting to
0.5.

If the review surface is later offered inside the prep app, it mounts the same REST API rather than
growing a second one. That matches the ruling already made for the agent driver in slice 5.

## Page kind is classified per book, and it runs before regions

Page kind cannot be decided from a single page, and the shipped classifier already proves it.
`fit_book_templates` measures every page in a book, takes the median first-band top and its
deviation, and only then classifies each page against that book's own templates. A book whose first
band wanders gets no templates rather than bad ones.

Two properties of that classifier carry forward. It refuses to guess, returning `unknown` for
anything between the head window and the chapter sink. And its residual against the fitted template
is a confidence signal already on disk.

Keep the refusal. The pages a classifier declines are exactly the ones a human should see first,
which is what the confidence queue in slice 5 is for.

That residual is not yet a confidence value, and turning it into one needs a measurement nobody
records. `template_residual_px` is a raw pixel distance, so it is unbounded and lower is better,
the opposite polarity to every other confidence here. It has to be inverted and scaled before
anything compares it to a threshold.

The scale must be per page class, and it does not exist. A normal page's residual is bounded by the
book's head window, which can be as small as 8 pixels.

A chapter opening's residual is measured against a template fitted from pages that sank by at least
150 pixels and by widely differing amounts. The same divisor would therefore push its confidence far
outside zero to one. `PageTemplate` carries only medians and counts, with no spread for the group it
was fitted from. Each template must start recording the spread of its own group before any of this
can be normalized.

Because the pass is book-scoped, it cannot run at page fetch. It has to be a job. That is the same
conclusion the proposal design reaches for a different reason, so the two agree.

The order per book is:

1. Measure geometry.
2. Propose page kinds for the whole book.
3. Let a person confirm what the model refused or was unsure about.
4. Propose regions conditioned on the confirmed page kinds.
5. Review those regions.

## Page kind needs a marker, not a decision log

A page has one page kind, so a human answer replaces it whole. The diff between the proposal and
the confirmed value already tells you whether the person accepted or changed it, provided something
records that a person looked. A per-page reviewed marker is enough.

The prep app has the right mechanism at the wrong granularity. `StageReviewStore` is a SQLite table
recording a confirmation with a timestamp, an actor, and a note, which is exactly the marker shape
this needs. But it confirms a whole stage for a project, meaning all pages reviewed for that stage,
so it cannot say which page a person looked at. Page kind needs the same record keyed per
page.

Do not model this on the `page_stage` row instead. That row's status tracks whether a pipeline
result is still valid, not whether a human reviewed it.

Regions are different. A page holds many, and a person may confirm some and ignore the rest, so
absence stays ambiguous and per-region disposition is required. The decision store is needed for
regions and not for page kind.

## Three page vocabularies already exist, and they are different axes

The region vocabulary spec absorbs PP-DocLayout's `RegionType` and DocLayNet. It does not absorb
either page vocabulary already shipping in the workspace, because its provenance covers
`pdomain-book-tools` and `pdomain-book-contracts` and never inspected the prep app.

| vocabulary | values | what it answers |
| --- | --- | --- |
| `PageClass` in `pdomain-pgdp-measure` | `normal_recto`, `normal_verso`, `chapter_opening`, `unknown` | which template this page's text block matches |
| `PageType` in `pdomain-prep-for-pgdp` | exactly seven: `normal`, `blank`, `plate_b`, `plate_p`, `plate_r`, `skip`, `cover` | what the packager does with this leaf |
| page kind, proposed here | title page, contents, body, index, plate, and the rest | what the page is |

Do not merge them. `PageClass` is a measured geometric signal that feeds a page-kind proposal.
Prep's `PageType` is a packaging decision derived from page kind plus policy. Page kind is the
thing a person confirms and a trainer learns.

**Call the new enum `PageKind`.** The roadmap and the split design both named slice 1's deliverable
`PageType`, and that name is taken by a shipped enum deciding what is written to the submission
zip. Both documents have been corrected.

The page model has a slot for this and no discipline on it. `Page` carries a free-form
`page_labels` list of strings with no allowed-values constant, and it round-trips. It also already
carries a `ReviewMetadata`. Page kind needs a typed field rather than a free-form list, so that a
value can be validated the way a region role is.

## What this does not settle

- The wire shape of a proposal record, and where the proposal store physically lives. The page
  blob's sidecar section and a separate blob are both candidates.
- Whether the decision store is a file beside the page blob or a table.
- The full page-kind vocabulary. It needs the same treatment section one gave the region roles.
- How a book-scoped proposal run reaches pages, given that the book labeling manifest is read-only
  today and has no write path anywhere in the labeler.
- The labeled-dataset contract the synthesizer reads at M16, which remains unspecified.

## Related

- [Region vocabulary](2026-09-07-region-vocabulary-design.md) — section one, the 34 roles and the
  additive-only rule.
- [Splitting measurement, labeling, and
  synthesis](2026-09-06-measurement-labeling-synthesis-split-design.md) — the design this carries
  out. Its claim that region proposals "copy this exactly" from the glyph pattern is corrected
  here: the glyph pattern cannot measure its own model, so regions must not copy it.
- [Labeling track roadmap](../plans/2026-09-07-labeling-track-roadmap.md) — the seven slices. Two
  of its statements are overridden here: regions persist as `Block` objects rather than a sidecar
  map, and slice 1's enum is `PageKind` rather than `PageType`.
