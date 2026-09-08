# Annotation provenance and persistence

## Agent Index

- **Kind:** spec
- **Status:** draft
- **Owner:** CT
- **Created:** 2026-09-07
- **Last verified:** 2026-09-08
- **Provenance:** designed 2026-09-07 and 2026-09-08 with the owner, from direct inspection of
  `pdomain-pgdp-measure/page_templates.py`, `pdomain-prep-for-pgdp/core/models.py`,
  `core/auto_detect.py`, `core/pipeline/stage_registry.py`, `api/data/project_stages.py`,
  `pdomain-ocr-labeler-spa/core/glyph/predictions.py`, `core/labeler_sidecars.py`,
  `core/page_state.py`, `core/jobs/runner.py`, `api/jobs.py`, `api/words.py`,
  `core/persistence/page_store.py`, `core/persistence/book_labeling_manifest.py`,
  `pdomain-book-tools/ocr/block.py`, `ocr/page.py`, `ocr/word.py`,
  `ocr/ground_truth_matching.py` and `ocr/layout_aware_reorg.py`,
  `pdomain-ocr-labeler-spa/core/typography_review.py` and `api/typography.py`, and
  `pdomain-book-contracts/ocr/glyph_annotations.py`, `ocr/review.py`, `typography/spans.py`
  and `typography/labels.py`
- **Disposition:** Draft. Sections two to five of the slice 1 and 2 design, extended on 2026-09-08
  to all five annotation levels. Complete as designed. No code has moved.
- **Read when:** deciding where a page-kind, region, style-span, word, or glyph annotation is
  stored, how a machine proposal is kept beside a human decision, how page kind is classified, or
  how the execution engine reads annotations without a human in the loop.
- **Search terms:** annotation provenance, region provenance, proposal set, decision log, page blob
  invariant, page kind, PageClass, PageType, StyleSpan, LabelSource, KnowledgeState,
  ConfidenceTier, TypographyCorrectionLog, confidence threshold, resolved regions, propose and
  confirm, ground truth provenance, ReviewMetadata source, ocr_confidence.

**Plan:** [Labeling track roadmap](../plans/2026-09-07-labeling-track-roadmap.md), slices 1 and 2.

**Spec:** [Region vocabulary](2026-09-07-region-vocabulary-design.md) is section one. This carries
sections two to five.

## What this settles

Machine proposals and human decisions live in separate stores that both persist. A single read
path resolves them into the regions a caller sees. Confirmed regions are `Block` objects in the
page blob. Proposals are per-run artifacts that are never edited. A third small store records what
a person decided about each proposal.

The same treatment applies at all five annotation levels: page kind, region, style span, word, and
glyph. Each must be built to the same standard, with no level left short. They start from very
different places, so the work per level differs sharply.

The reason is measurement. You cannot score a model unless you keep what it said beside what the
person chose. Two shipped features in the suite overwrite one with the other and so cannot be
scored. `StyleSpan` is the exception that already does all of it, and it is the pattern the other
four adopt.

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

This matters beyond bookkeeping. F2 alignment is best effort, and neither side of it is ground
truth. A trainer that reads `ground_truth_text` without knowing its origin cannot tell a confirmed
reading from an alignment guess.

The fix is the `source` field this design puts on `ReviewMetadata`, applied at word level. No new
store is needed.

## Five levels need this, and the pattern to copy is `StyleSpan`

Annotation happens at five levels, each feeding a different model. All five must be built to the
same standard, by owner direction on 2026-09-08. None may be left with gaps.

| level | what it holds today | trains |
| --- | --- | --- |
| page kind | a free-form `page_labels` list, no allowed values | the page classifier |
| region | nothing | the layout detector |
| style span | `StyleSpan`, complete | style |
| word | `text` and `ocr_confidence` beside `_ground_truth_text` | OCR recognition |
| glyph | `GlyphAnnotations` and a `char_bboxes_map` sidecar | the glyph inventory and synthesizer exemplars |

**Copy `StyleSpan`, not the glyph accept-prediction route.** The split design told us to copy the
glyph pattern. That pattern is the weakest instance in the suite. `StyleSpan` in book-contracts is
the strongest, and it already carries everything this design asks for.

Its three vocabularies are richer than a human-or-machine flag. `LabelSource` names five origins:
`f2`, `gutenberg_html`, `se_computed_css`, `human`, `synthetic`. `ConfidenceTier` is `gold`,
`silver`, `bronze`, `quarantine`. `KnowledgeState` is `positive`, `verified_negative`, `unknown`,
`conflict`.

**`LabelSource` needs a sixth member before it can serve this track.** Its five values are four
document sources and a person, because it was built to record which transcription asserted a style.
It is referenced in exactly one place today, the F2 parser. Nothing in it can say that a model
proposed something, which is the claim this entire track exists to record. Add `model`. The model's
identity and version stay on the run record rather than in the enum, so the vocabulary stays small
and identity is not duplicated.

That third enum is the one the other levels lack. `verified_negative` is a recorded rejection, and
`conflict` names two sources disagreeing. A span also carries `source_slices`, `rule_ref`,
`semantic_reason`, and `warnings`, which is its evidence.

## Built properly means eight properties, and `StyleSpan` has all eight

1. The machine's claim persists.
2. The human's answer persists separately from it.
3. Provenance names which source produced the answer.
4. Confidence is recorded.
5. Evidence is recorded.
6. A rejection is expressible, not merely an absence.
7. Unreviewed is distinct from reviewed-and-empty.
8. Two sources disagreeing is expressible.

The decision store this implies is also already built. `TypographyCorrectionLog` is a project-local
JSONL journal at `.pd-pages/typography-corrections.jsonl`. It fsyncs before append returns and never
rewrites an existing record. It represents supersession through a revision chain, and it takes an
operating-system append lock so writers across worker processes serialize.

So the annotation model and the decision store both exist. The work is generalizing them to the
other four levels, not inventing either.

## What each level is missing

**Page kind has nothing typed.** `page_labels` is a free-form list of strings with no
allowed-values constant. It needs the `PageKind` enum, a per-run classifier proposal, and a
per-page reviewed marker.

**Regions have nothing at all.** Role labels round-trip on `Block` and that is the whole of it.
Everything in this design is new work here.

**Style spans have the model, no identity, and the wrong review granularity.** No route lets a
person confirm a span. The typography review routes are word-scoped, at
`/typography/words/{word_id}/`, while the model is a grapheme range that crosses word boundaries.
The labeler already loads spans: `book_labeling_session.py` validates `TypographyPageRecord`, whose
`style_spans` field is deserialized on every page-record load. It then discards them, retaining
nothing on the loaded bundle.

**`StyleSpan` also carries no identifier of its own.** The eight properties above do not ask for
one, but a decision store does. A page holds many spans, so by the rule below they need per-span
recorded disposition, and a disposition has to point at something. Identity must be derived
deterministically from the page digest, the range, and the content before any span-level decision
can be stored.

**Words have the two stores and no provenance.** `ReviewMetadata` holds only `validated`,
`reviewer_note`, and `flagged_for_attention`. It can express neither a rejection nor a conflict, and
it cannot say which of the four writers filled `ground_truth_text`.

**Glyphs have provenance and throw away the evidence.** `GlyphAnnotations.source` has three values,
but predictions are never persisted, there is no reject route, and there is no confidence or
evidence field. The `char_bboxes_map` sidecar is keyed positionally, which the geometry rule above
forbids.

## Two models replace PP-DocLayout eventually, and run versioning is what makes the swap measurable

The goal is our own book layout model and our own page layout model, by owner direction on
2026-09-08. Two models, matching the two scopes this design already separates: a book-scoped model
proposing page kind, and a page-scoped model proposing regions.

Run versioning is what turns the swap into a measurement rather than a leap. Every run records its
model identity and version, so a new detector is simply a new run over the same pages. The earlier
runs and the human decisions against them stay valid, which means the replacement can be scored
against PP-DocLayout on identical pages with identical human answers. That comparison exists only
because proposals persist.

One of the two seams is already open and the other does not exist. `register_detector` in
`pdomain_book_tools/layout/registry.py` is an extension point documented for downstream projects
and called by nobody. `PPDocLayoutPlusLDetector` accepts a `checkpoint_path`, and `pdomain-ocr-cli`
exposes `--layout-checkpoint`, so a page-level detector can be swapped today. Nothing equivalent
exists at book level. `fit_book_templates` is a fitted heuristic rather than a pluggable model, so
a book-scoped classifier has no seam to plug into.

## When a decision store is required, and when a marker is enough

The three cases in this design need different amounts of machinery, and one rule explains why.

**A decision store is required only when the human's answer is sparse against the machine's
output.** A page holds many regions and a person may confirm some and ignore the rest, so absence
stays ambiguous and each proposal needs its own recorded disposition.

**Otherwise a diff plus a reviewed marker is enough.** A word has one answer and a page has one
kind, so the human's answer replaces the machine's whole. Comparing the two tells you whether it
was accepted or changed, and the marker tells you somebody looked.

So regions and style spans get all three stores, because a page holds many of each. Words and page
kind get two stores and a marker. Glyphs follow words, since a word has one glyph annotation set.

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

## The routes follow the convention already in place

Region routes add nothing agent-specific, because the existing convention already serves both
callers. The word and page routes take the per-page lock, bump `generation`, persist, and return
the full `PagePayload`. Region routes do the same, so a person clicking and an agent calling see
identical semantics.

**That convention is not universal, and the exception is instructive.** The typography routes take
the page lock but return a compare-and-swap `head_token` and check an `expected_head` on write,
with no `generation` and no `PagePayload`, because style spans never enter the page state that
payload is built from. Any annotation level whose data does not live on the page follows the
typography pattern rather than this one.

Eight routes carry the work:

- create a region
- edit a region
- delete a region
- set a region's word membership
- accept a proposal
- reject a proposal
- list a page's proposals, with confidence and evidence
- start a book-scoped proposal run, which returns a job id and reports through the existing
  `/api/jobs` event stream

Two of those deserve note. Setting membership is its own route because membership is an explicit
edge rather than a consequence of geometry. And reject is the counterpart the glyph pattern never
got, which is the reason that pattern cannot measure itself.

`PagePayload` grows regions and proposals. Whole-page state in one call already exists as
`GET /api/projects/{project_id}/pages/{page_index}`, and because every mutation returns that same
payload, an agent never needs a second call to see what changed.

The review queue is the only piece built from nothing. No queue, ranking, triage, or next-page
endpoint exists in any of the 21 router modules, and the sole occurrence of `confidence` in the
whole route surface is an auto-rotation threshold.

**Give these routes explicit `operation_id` values**, which the repository does not do today. There
is no `operation_id` anywhere and no `generate_unique_id_function`, so FastAPI derives identifiers
from the function name and a path hash, and they change when a route moves. Those identifiers are
what a generated client calls. The contract is already gated, since `frontend/src/api/types.ts` is
committed and a CI job fails on drift, so stable identifiers are what make it usable.

## Reading order follows explicit membership, not geometry

A region's box is not its membership, so geometry only proposes which words a region holds.
`tag_words_with_layout` assigns a word to every region containing the word's bounding-box centre,
and containment is an axis-aligned rectangle test, `L <= x <= R and T <= y <= B`.

The rectangle over-tags, and that is deliberate. Body text flowing around a ragged figure sits in
the notch of the figure's bounding rectangle, so every one of those words tests as inside the
figure. A true polygon would exclude them; a bounding box cannot.

**The over-tagging is load-bearing, and an earlier draft of this design was wrong to call it simply
a defect.** `_word_has_only_layout_tag` reads how many `layout:` tags a word carries and treats a
word tagged both `layout:figure` and `layout:text` as wrap-around body rather than figure-internal
noise, so it is not dropped. Multi-tagging is how the shipped pipeline already disambiguates the
ragged figure.

So the change is layered, not a replacement. The tagging pass keeps its multi-tag output, because a
downstream pass reads the multiplicity as evidence. What changes is that this output becomes a
proposal rather than an answer, and stored membership on a confirmed region is an edge somebody
confirmed. Exclusive membership binds confirmed sibling regions; it does not bind the proposal
layer, where a word being a candidate for two regions is exactly the signal worth keeping.

**Sibling regions are disjoint, ancestors are not.** Two siblings may overlap as rectangles and
still share no word. A word belongs to several regions only through ancestry, which the block tree
gives for free. So the owning region is always the innermost one, and no tie-break rule is needed.

**`Block` enforces the opposite relationship today, and that has to be reconciled.** Both
`Block.add_item` and `Block.remove_item` end by calling `recompute_bounding_box`, so a block's box is
derived from its members. Changing a region's membership would silently redraw its box to the union
of its words, which is exactly what the rule above forbids. A region's box is an independent fact
that a person or a detector asserted, and it must survive a membership change untouched, so every
membership write has to preserve it explicitly.

**Order stays derived, with an explicit override.** Order is recomputed on every access to
`page.items`, sorting by `override_page_sort_order` where it is set and by top-left y then x
otherwise. That override is a real integer field on `Block` that round-trips through `to_dict` and
`from_dict`, so the split design was wrong to say nothing serializes reading order. Sidenotes and
captions already use it, pinning left-margin notes before the body and right-margin notes after.

**The preservation check needs a duplication check.** `validate_word_preservation` compares word
signatures before and after reorganization, reports only missing words, and explicitly permits
extras. Duplication is never checked. That was safe while membership was many-to-many. Once
siblings are disjoint, one word in two regions is a violation and nothing today would catch it.

**Dropped words become a queue signal.** When words go missing, `reconcile_dropped_words` either
raises under `PD_OCR_REORGANIZE_STRICT` or wraps them in a synthetic block with the `recovered`
role. Those blocks mark ink the pipeline could not place, which is what a person should see first.

One constraint carries over from section one: `route_sidenote_reading_order` matches the literal
string `"sidenote"`, so the additive-only rule is what keeps it working.

## The test plan uses the four tiers that exist

The labeler runs 105 unit files, 59 integration files against a live stack, 24 Playwright files in
CI, and 2 conformance files over golden fixtures. Markers are strict and warnings are errors.
Region work slots into those tiers and adds no fifth.

**Two invariant tests matter more than route coverage, and both are cheap.**

Run a proposal job over a page, then assert the page blob's content hash is unchanged. Content
addressing makes that a one-line assertion, and it is the single test that stops machine output
becoming ground truth by accident.

Then assert no word is a member of two sibling regions. This is where the duplication gap closes:
the check and its test land together.

**Three tests prove the design does what it claims.** Accepting a proposal must leave the proposal
record byte-identical, with a decision record naming it. Rejecting one must produce a
`verified_negative` decision, so a rejection is distinguishable from an unreviewed proposal.
Relabeling a page kind must leave earlier region proposals still naming the page-kind decision they
read, marked stale rather than silently reused.

**The resolver gets a table test whose most important row is the empty one.** Confirmed region
present, proposal above threshold, nothing at all. The row that matters most has both human stores
empty and a real threshold set, because that is the execution engine running unattended. If it
passes, the production path is covered by the same test as the labeler.

**Round-trip goes to conformance with a golden fixture,** pinning `block_role_labels` and
`override_page_sort_order` so a future `Block` change cannot quietly drop either.

**Two things come free.** The committed `types.ts` and the `openapi-drift` CI job contract-test the
new routes without anything being written. And `test_torch_free_import.py` in book-contracts
already blocks torch, doctr, torchvision, cv2, pandas, matplotlib, and transformers, so slice 1's
enum is covered the moment it lands.

**One browser test earns its cost:** proposals must render visibly distinct from confirmed regions.
That is the guard against treating model output as data, and it is only observable in a browser.

**One existing fixture must not be mistaken for ground truth.** The 120-case layout regression
fixture in book-tools stores PP-DocLayout's own output as its expected values. It detects change
and cannot validate correctness.

## Six corrections from the data-model scan

A scan on 2026-09-08 read the design against all eight plans and the code, looking for things the
data model cannot represent rather than work with no plan. Six findings are settled here because
they follow from rules already made.

**Regions nest, and the plans made them flat.** The vocabulary spec's hierarchy rule 1 expresses
containment by nesting, and rule 6 requires a `BlockCategory.GROUP` holding a `brace` or `bracket`
plus a `group label`. `BlockCategory` has only `BLOCK`, `PARAGRAPH`, and `LINE`, and a region
created with `child_type=BlockChildType.WORDS` raises `TypeError` when a child block is added. So
the vocabulary can name `brace`, `bracket`, `group label`, and a `page header` containing a running
head and a folio, while the only write path cannot build any of them. Region creation must accept a
nesting-capable child type, and `BlockCategory.GROUP` must exist before those four roles mean
anything.

**`ResolvedRegion` must carry word membership.** It holds a role, a box, and provenance and no
words. That makes the single read path unable to answer the question a trainer actually asks, and
forces every caller to walk the block tree itself, which defeats having one path at all.

**A confirmed region must record where it came from.** A region created by hand and a region
promoted from a proposal are currently byte-identical, because only `region_id` is stamped. Record
the originating proposal id, or an explicit marker meaning a person drew it unprompted.

**Glyph identity must be geometric, on the same grounds as regions.** The glyph annotation and
prediction maps stay keyed on line and word ordinal. Line numbering is not stable across the
band-identification fixes, and matching on ordinal across a renumbering already invalidated an
analysis in this repository. The rule that forbids positional keys for regions applies unchanged
one level down.

**Glyphs adopt `LabelSource` now that it can name a model.** The glyph level keeps a private
three-value source vocabulary because nothing in `LabelSource` could say a model predicted
something. Adding `model` removes that reason, so the levels share one vocabulary as the design
requires.

**The proposal run reads the page-kind state itself.** Passing the page-kind reference in as a
request field lets a caller run region proposals against a book whose page kinds were never proposed
or confirmed, which silently breaks the ordering the design depends on. The job looks the decision
up rather than trusting what it was handed.

## Editorial corrections say what the page should have said, and never touch ground truth

The five annotation levels all describe what is on the page. An editorial correction is the one
thing that departs from it: the ink reads one way, and context or editorial direction says it should
read another. A printer's error, a dropped word, a name misspelled consistently through a chapter.

**The invariant is that an editorial correction never enters `ground_truth_text`.** Ground truth is
what the ink says, always. If "should have said" leaks into it, the recognition trainer learns to
read words that are not on the page, and the corpus this track exists to produce is quietly
poisoned. The correction sits beside the reading, never inside it.

The suite already runs this discipline for one case. The F2 parser captures PGDP's `[** ... ]`
proofer notes as `ParserNoteEvidence`, whose own docstring calls them quarantined, holding
`raw_text`, `page_review_content`, a status, and source slices. Separately, `remove_proofer_notes`
strips them from the text. Captured and held apart, never applied. An editorial correction
generalizes that from PGDP's note convention to any correction from any source.

**A correction is span-scoped, and its span may be empty.** Corrections cross word boundaries, so
the word level is the wrong home. They also insert: a word the printer omitted has a correction with
no extent in the ink at all. `StyleSpan` cannot serve here, because its range validator requires
`start < end` and so forbids the zero-width insertion. Editorial corrections need their own model.

Each correction records the reading as printed, the reading intended, and why — a printer's error, a
missing mark of punctuation, a modernization, an editorial conjecture. Provenance and knowledge
state come from the same shared vocabularies as everything else, so a conjecture and a certain fix
are distinguishable, and a correction can be rejected on review like any other claim.

**The labeler records them. A post-processor applies them.** Owner direction, 2026-09-08. Applying a
correction is out of scope here and belongs to a post-processing stage that does not yet exist. The
synthesizer never sees corrections at all, because it renders what the ink said.

## Glyph marks point into mutable text, and go stale unnoticed

Glyphs sit below words, so a glyph annotation set hangs off one word and is keyed by that word. That
much the identity rule above already covers. Below the word it is worse, and this is live today.

`LigatureMark.char_span` is a half-open pair of character indices into `Word.ground_truth_text`, and
`long_s_positions` is a list of character indices into the same string. That string has four
writers: F2 alignment, a person typing, split and merge redistributing tokens, and the export job.
Correcting a word's ground truth shifts every mark on it, and nothing invalidates or remaps them. A
ligature span survives the edit and now names different characters.

This is the ordinal problem one level down. It does not touch Gate 3: `pdomain-pgdp-measure` never
reads these marks, so the glyph inventory Gate 3 scores is built from a different path. What is at
risk is everything downstream of the labeler's own glyph annotations, which the labeler passes
straight to its wire model without checking them against the text they index. That is the corpus
this track exists to produce.

The fix is the mechanism the page level already uses. Store a digest of the ground-truth text
alongside the annotation set. When the text changes, the digest stops matching and the sub-word
marks are stale rather than silently wrong. Facet digests at page level, a text digest at word
level, one rule.

## A proposal goes stale per facet, not per page

A whole-page content hash is too blunt. Fixing one typo would invalidate every geometry proposal on
the page, even though nothing the geometry depended on moved. So a run records what it actually
read, and staleness is decided against that.

**Owner ruling, 2026-09-08: staleness is decided per edit kind.** A text correction leaves geometry
proposals valid; a rebox or a split invalidates them.

The mechanism is a digest per page facet rather than one hash for the page. A run stores, for each
page it read, a digest of each facet it depended on. At read time the resolver recomputes those
facets from the current page and compares only the ones the run named. Four facets carry the
distinctions that matter:

| facet | covers | a geometry proposal depends on it |
| --- | --- | --- |
| `word_boxes` | every word's bounding box | yes |
| `line_structure` | line and paragraph grouping, and their order | yes |
| `page_image` | the image blob the detector ran on | yes |
| `word_text` | OCR text and ground-truth text | no |

**Facet digests are computed, never declared.** An earlier draft had every mutation route announce
what it touched. Recomputing the digest gives the same answer without a hand-maintained list that
can drift out of step with the route it describes, and it catches a change no matter which path
made it.

A proposal whose named facets still match is current. One whose facets have moved is served with a
stale marker, so a person still sees what the model said and judges it against the page as it now
stands. The resolver therefore needs the page's current facet digests as an argument; without them
staleness cannot be seen at read time at all.

## An accepted decision carries forward, and says so

**Owner ruling, 2026-09-08: a decision carries across runs, recorded as its own disposition.**
Proposal ids are minted fresh per run, so without this a person re-reviews the whole corpus on every
model upgrade, which in practice stops upgrades happening.

When a run proposes a region that matches one a person already confirmed, by geometric overlap and
agreeing role, the earlier decision carries to the new proposal. The carried decision is written as
`carried`, not `accepted`, and names both the run it came from and the proposal it came from.

The separate disposition is what keeps measurement honest. A carried decision is not fresh human
agreement and must never be counted as though it were, or every model would score better simply by
being run later. It also lets a person filter for carried decisions and spot-check them.

## What this does not settle

- The wire shape of a proposal record, and where the proposal store physically lives. The page
  blob's sidecar section and a separate blob are both candidates.
- Whether the decision store is a file beside the page blob or a table.
- The full page-kind vocabulary. It needs the same treatment section one gave the region roles.
- How a book-scoped proposal run reaches pages, given that the book labeling manifest is read-only
  today and has no write path anywhere in the labeler.
- The labeled-dataset contract the synthesizer reads at M16, which remains unspecified.
- The post-processor that applies editorial corrections. Its input shape is settled here; nothing
  else about it is.
- Whether an editorial correction can span a page boundary. A word broken across pages is already
  known to be handled poorly, and a correction to one is unmodeled.

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
