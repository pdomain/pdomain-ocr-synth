# Region vocabulary for historical book page labeling

## Agent Index

- **Kind:** spec
- **Status:** draft
- **Owner:** CT
- **Created:** 2026-09-07
- **Last verified:** 2026-09-07
- **Provenance:** designed 2026-09-07 with the owner, from direct inspection of
  `pdomain-book-tools/pdomain_book_tools/ocr/block.py`, `dropcap.py`, `layout_aware_reorg.py`,
  `layout/_mappings.py`, `pdomain-book-contracts/pdomain_book_contracts/layout/types.py`, and
  `pdomain-book-tools/docs/specs/10-table-structure.md`; reviewed in two adversarial passes plus
  a recheck, with corpus evidence sampled from `/workspaces/pdomain-data/pgdp-corpus`
- **Disposition:** Draft. Section one of the slice 1 and 2 design is settled and reviewed. The
  routes, reading order, and test plan are not yet written. No code has moved.
- **Read when:** adding or changing a page region role, mapping a layout detector into the page
  model, or deciding where structure belongs against where meaning belongs.
- **Search terms:** region role, RegionRole, block role labels, page furniture, catchword,
  signature mark, speaker label, stage direction, decorated initial, additive only, BlockCategory.

**Plan:** [Labeling track roadmap](../plans/2026-09-07-labeling-track-roadmap.md), slices 1 and 2.

**Spec:** [Splitting measurement, labeling, and
synthesis](2026-09-06-measurement-labeling-synthesis-split-design.md)

## Review history

Two adversarial reviews and one recheck. The first round returned nine findings, all verified
against the code; the recheck returned four, all verified and folded in.

The reviews changed the design twice in ways that mattered. Every rename proposed in revision 1
would have silently broken shipped code. And a `drop cap` region role was withdrawn, then partly
reinstated as `decorated initial` once the recheck showed a purely graphic initial has no home at
either the word or the region level.

## Purpose

A human-labeling vocabulary for page regions in historical printed books, scanned by
Distributed Proofreaders (PGDP). It becomes the authority that `Block.ALLOWED_BLOCK_ROLE_LABELS`
is derived from, and the target that PP-DocLayout's `RegionType` proposals map into.

Consumers: `pdomain-ocr-labeler-spa` (human confirms), a geometry proposal engine, a future
layout model trained on the confirmed corpus, and `pdomain-ocr-synth` (renders synthetic pages
from labeled data).

## The governing rule: additive only

**No shipped role string is renamed. The vocabulary only grows.**

Revision 1 proposed renaming `sidenote` to `marginalia`, `page number` to `folio`, `paragraph` to
`body_text`, `section` to `heading`, and `decoration` to `ornament`. Every one of those breaks
working code that matches the literal string:

- `route_sidenote_reading_order` tests `"sidenote" not in block.block_role_labels`
  (`pdomain_book_tools/ocr/layout_aware_reorg.py:741`). Renaming disables left/right sidenote
  reading-order routing.
- `dropcap._SKIP_ROLES` holds the literals `"sidenote"`, `"page number"`, `"page header"`,
  `"page footer"`, `"poetry"`, `"blockquote"`, `"recovered"`, `"printers mark"`
  (`pdomain_book_tools/ocr/dropcap.py:66-79`). Renaming disables drop-cap skip logic.
- `figure` and `illustration` are not synonyms. `_REGION_TO_BLOCK_ROLE` stamps `figure` on a
  figure region containing OCR text; `_empty_illustration_block` stamps `illustration` on a
  text-less placeholder (`layout_aware_reorg.py:107,798`). Aliasing collapses a live distinction.

Canonical strings use spaces. `BLOCK_ROLE_LABEL_ALIASES` already folds no-space variants in
(`pageheader`, `printersmark`, `poem`). New roles follow the same convention.

## Two orthogonal axes, plus one that already exists

- **`BlockCategory` carries structure.** Existing: `BLOCK`, `PARAGRAPH`, `LINE`. Adding `TABLE`
  and `CELL` (from `pdomain-book-tools/docs/specs/10-table-structure.md` §6.1) and `GROUP`
  (braced sets). Structure gets typed fields where needed: `row`, `col`, `rowspan`, `colspan`
  on `CELL`.
- **`RegionRole` carries meaning.** The 34 values below.
- **`word_components` already carries sub-word features.** *Textual* drop caps live here, tagged
  `word_components=["drop cap"]` by `dropcap.py`. Revision 1's `drop cap` region role is
  withdrawn for that case only. A purely graphic or historiated initial has no recoverable
  letter, never becomes a `Word`, and is unmodeled today: the failure path `_tag_unrecovered`
  (`dropcap.py:541-547`) stamps `"drop cap unrecovered"` on the *adjacent body word*, not on the
  graphic. That case gets the region role `decorated initial`.

They compose: a `CELL`-category block may carry role `poetry`.

## The 20 existing roles, unchanged

`paragraph`, `sidenote`, `page header`, `page footer`, `page number`, `printers mark`,
`blockquote`, `poetry`, `recovered`, `illustration`, `decoration`, `caption`, `figure`, `table`,
`footnote`, `title`, `section`, `list`, `formula`, `artefact`

`page header` and `page number` already give the running-head against folio distinction that
revision 1 proposed inventing.

## The 14 additions

| role | why | evidence |
| --- | --- | --- |
| `signature mark` | the gathering identifier the binder used, `B`, `B2`, `*3`; sits where a folio sits and is confusable with it | no ground-truth text; F2 strips furniture |
| `catchword` | first word of the following page | the synthesizer already plans italic catchwords: `pdomain-ocr-synth/docs/specs/00-overview.md:83`, `12-glyph-annotations-emission.md:125` |
| `press figure` | the pressman's number, 18th-century English books; same confusable family as folio | narrowest of the additions |
| `rule` | horizontal rules separating footnotes, headers, sections | named in the synthesis design |
| `brace` | curly grouping glyph | synthesis design models braces as structural objects |
| `bracket` | square grouping glyph | as above |
| `group label` | what a braced or bracketed set resolves to | needed to make the group a relation, not a box |
| `plate` | full-page or fold-out illustration, often unpaginated, no co-resident text, outside reading order | corpus: `projectID63b4e1e68a96d`, `projectID68abc81304cd5`; alias `frontispiece` |
| `speaker label` | drama; outdented name above indented dialogue, recurs many times per page | corpus: `projectID65cfe77f57e7a`, `projectID60ffe3563537d` |
| `stage direction` | drama; set apart from dialogue, distinct from `blockquote` | as above |
| `interlinear gloss` | word-by-word gloss between two lines of one paragraph; no other role can express that position | `pdomain-ocr-synth/docs/specs/00-overview.md:112` puts English-grammar-of-Irish pages in scope |
| `abandoned` | PP-DocLayout emits it; `Block` has no target | `RegionType.abandoned` |
| `decorated initial` | graphic or historiated initial with no recoverable letter; unmodeled at both word and region level today | `dropcap.py:541-547` tags the neighbouring word, never the graphic |
| `unknown` | explicit "not yet decided", distinct from unlabeled | needed for the review queue |

New aliases: `frontispiece` to `plate`, `signaturemark` to `signature mark`, `pressfigure` to
`press figure`, `stagedirection` to `stage direction`, `speakerlabel` to `speaker label`.

## Hierarchy rules

1. Containment is expressed by nesting. No role is inherently container or leaf.
2. A `LINE` block holds words directly and never child blocks. (Existing invariant R-14,
   `block.py:185`.)
3. One band of ink may produce several line blocks. A running head and a page number are always
   separate blocks even when they sit on the same physical line.
4. Every word reaches a leaf block or the `recovered` block. **Known exception:**
   `build_recovered_words_block` filters any dropped word lacking a bounding box
   (`reorganize_page_utils.py:898`), and `reconcile_dropped_words` returns unchanged when the
   result is `None` (same file, 996-998). Such words are lost silently in non-strict mode. This
   rule describes the intent; the gap is real and tracked separately.
5. Boxes may overlap freely. **A machine may propose ownership from box geometry** — the table
   spec assigns words to cells by box overlap with a nearest-cell fallback
   (`10-table-structure.md:327-328,432-434`). **A confirmed label states ownership explicitly**
   and is never re-derived from geometry afterwards. The fallback for a word matching no cell is
   *unresolved*: `10-table-structure.md` §9.2 lists nearest-cell snap, a synthetic edge cell, and
   non-table placement as undecided alternatives.
6. A braced set is `BlockCategory.GROUP` containing a `brace` or `bracket` child, member blocks
   keeping their own roles, and a `group label`. Direction and orientation use existing
   `block_position_labels`: `left`, `right`, `top`, `bottom`, `center`. **This requires a new
   sort branch.** `_sort_items` (`block.py:318`) sorts on bounding boxes alone and
   branches on neither category nor position labels. (`region_reading_order` in
   `pdomain-book-contracts` is *not* relevant here: it orders pre-OCR `LayoutRegion` objects,
   which carry no `BlockCategory`, at a different pipeline stage.) The table spec added an
   explicit `TABLE` branch for this reason
   (§6.2). `GROUP` needs the same, ordering members before the label regardless of geometry.
   `_sort_items` already carries a TODO describing an intended role-aware order it does not
   implement (`block.py:319-333`).

## A signal we currently discard

`PP_DOCLAYOUT_TO_PGDP` maps PP-DocLayout's native `page_number` label to `footer`
(`pdomain_book_tools/layout/_mappings.py:34`), with a comment that PGDP treats it as
bottom-margin chrome. The detector can see the folio and we delete the answer before it reaches
block roles. Nothing can propose `page number` automatically today for this reason alone.

Fixing this is three edits in two repos, not a dict-value change. `RegionType` has no
`page_number` member (it has `abandoned`, but not this), so it needs one added, plus a
`_REGION_TO_BLOCK_ROLE` entry mapping it to the already-existing `"page number"` block role,
plus the `PP_DOCLAYOUT_TO_PGDP` change. Adding a member does not contradict the split design's
ruling that `RegionType` "stays as it is" — that ruling forbade merging it with the human
vocabulary, not extending it.

## Vocabularies this must absorb

**PP-DocLayout `RegionType`, 14 values** (`pdomain_book_contracts/layout/types.py`), which stays
as a separate enum recording what a detector proposed: text, title, section, list, table, figure,
decoration, caption, header, footer, footnote, formula, abandoned, sidenote.

**DocLayNet, 11 classes**, used by deepdoctection and Docling: Caption, Footnote, Formula,
List-item, Page-footer, Page-header, Picture, Section-header, Table, Text, Title.

## Deliberately excluded

- `table_row`, `table_cell` — table structure is on the category axis with typed grid
  coordinates. String roles would duplicate it more weakly.
- `list_item` — there is no list-structure analogue to the cell grid fields. **`list` is
  therefore scoped to flat runs**, and nested or ordinal list structure is out of scope until
  something needs it.
- `drop cap` — already a `word_components` value, handled by `dropcap.py`.
- `map`, `portrait`, `diagram`, `chart` — content classification, not layout. Unbounded, not
  separable by geometry, usually stated in the caption.

## Known constraints and open items

- Must import with no imaging or ML stack. `pdomain-book-contracts/tests/test_torch_free_import.py`
  blocks torch, doctr, torchvision, cv2, pandas, matplotlib, transformers.
- PGDP F2 transcription strips running heads and page numbers entirely, so all page furniture is
  `recognized` tier, never `transcribed`. It has no ground-truth text, and Gate 3 has never
  measured it.
- No region ground truth exists anywhere in the suite today.
- **Open:** how a pre-structure `block_role_labels=["table"]` becomes a post-structure
  `BlockCategory.TABLE`. `10-table-structure.md:475` lists this as unresolved in its own review.
  Deferred to that spec.
- **Two page vocabularies this spec did not absorb.** Its provenance covers `pdomain-book-tools`
  and `pdomain-book-contracts` and never inspected `pdomain-prep-for-pgdp`, which ships a
  seven-value `PageType`, or `pdomain-pgdp-measure`, which ships a four-value `PageClass`. The
  companion spec on [region provenance and
  persistence](2026-09-07-region-provenance-and-persistence-design.md) treats them as three
  separate axes and names the new enum `PageKind` to avoid the collision. This affects the page
  enum only; the 34 region roles are unaffected.
