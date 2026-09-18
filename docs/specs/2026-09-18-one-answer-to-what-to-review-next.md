---
Status: draft
Owner: CT
Created: 2026-09-18
Last verified: 2026-09-18
Kind: spec
---

# One answer to what to review next, across every kind of work

## Agent Index

- **Kind:** spec
- **Status:** draft
- **Owner:** CT
- **Created:** 2026-09-18
- **Last verified:** 2026-09-18
- **Provenance:** authored 2026-09-18 from a measured inventory of every kind of
  review work in `pdomain-ocr-labeler-spa` at `a9a90fb`, taken on 80 real pages
  and 18,463 real words of `projectID3fc3d7d03c613`; sources read include
  `api/regions.py` (`get_region_review_queue`), `api/page_kinds.py`,
  `api/words.py` (`_apply_word_validated`), `api/typography.py`,
  `core/page_state.py` (`save_page_content_to_store`),
  `core/glyph/predictions.py`, `core/jobs/handlers/export.py` and
  `core/jobs/handlers/propose_regions.py`
- **Disposition:** Draft. The last owed increment of slice 5 of the labeling
  track, after the [book review queue](2026-09-17-book-review-queue-design.md)
  and [page-kind review](2026-09-17-page-kind-review-design.md).
- **Read when:** adding a kind of review work to the queue, counting outstanding
  work for a book, or wondering why word counts are not free.
- **Search terms:** review queue, what to review next, outstanding work, word
  validation count, typography completion, review counts journal, slice 5.

## One route and one journal answer every kind of review work

This design adds one route that answers for every kind of work, in the order
the work actually has to happen. It also adds one small journal that makes two
of those kinds, words and typography, countable at all.

A person reviewing a book has one question, but today's product answers only
part of it. `GET .../regions/review-queue` says how many region proposals are
undecided. Nothing says how many pages still need a kind, how many words still
need validating, or how much typography review is outstanding. The rail badge
counts regions and calls itself the review queue.

## The kinds, and what each costs to count

Measured on 80 pages and 18,463 words of `projectID3fc3d7d03c613`.

| kind | source | cost |
|---|---|---|
| region proposals | two JSONL journals, read once each | 0.41 ms, 1.46 ms on a larger run |
| page kinds | two JSONL journals, read once each | 0.74 ms |
| words | the string `validated` inside each page's content blob | 42 to 46 ms a page to parse, about 14 s for 300 pages |
| typography | a journal for the numerator, the page for the denominator | measured: about 80 µs a row — 15 ms at 1% of a book's words corrected, 1.5 s at 100%; denominator as above |
| glyphs | nothing produces predictions | no work exists to count |

**Regions and page kinds are already cheap**, because a person's decision about
them lands in an append-only journal that can be read without opening a page.

**Words are not, and that is the whole problem.** A word counts as reviewed
only when its `Word.word_labels` field holds the string `validated`, and that
field lives only inside the page's content blob. Counting a book means parsing
every page. That is the same shape the project list rejected on 2026-09-18 at
206 ms against 22 ms, and this is worse.

**Typography's numerator is measured, and it is not cheap once a book has
real correction history.** The one book measured has no typography correction
history, so its journal was effectively empty and said nothing about cost at
scale. A fixture built afterwards, at the same 18,463-word scale, with real
correction rows at several coverage levels, timed
`TypographyCorrectionLog.records()` plus the reviewed-word filter together:

| corrections | rows | file size | time |
|---|---|---|---|
| 1% of words | 184 | 421 KB | 15 ms |
| 5% of words | 923 | 2.1 MB | 68 ms |
| 10% of words | 1,846 | 4.2 MB | 143 ms |
| 25% of words | 4,615 | 10.6 MB | 355 ms |
| 100% of words | 18,463 | 42.3 MB | 1,521 ms |

The cost is in parsing every row of the corrections journal: about 80
microseconds a row, almost entirely pydantic's validation of each row's
nested `WordTypography` replacement rather than the file read itself (raw
JSON parsing alone was 36 ms of the 143 ms at 10% coverage; pydantic
construction accounted for the rest). This is why the labeler's review-queue
route reports the typography kind `available: false` with a reason above a
512 KiB journal size (about 224 rows) — the size a single `stat()` call, not
a read, can rule out in advance — rather than compute a count that can cost
over a second. Below that size the read stays in the low tens of
milliseconds (about 16 ms at 512 KiB itself). The real fix is a per-page
typography rollup written where a correction is accepted, the same shape as
the word-review-counts journal; see `pdomain-ocr-labeler-spa`'s
`docs/issues/2026-09-18-typography-numerator-needs-a-per-page-rollup.md`.

**Glyphs have nothing to count.** `IGlyphPredictor.predict` is never called,
only `NoneGlyphPredictor` exists, and 0 of the 18,463 real words examined carry
a glyph annotation. A person's own glyph marks persist and could be counted at
page-blob cost, but there is no machine backlog to work through.

## A per-page count journal, written where the page is already saved

Every word, line, paragraph and job mutation funnels through one function,
`save_page_content_to_store` in `core/page_state.py`. It already serializes the
page and hashes the blob. Counting the page's words while it does that costs
0.20 ms, negligible next to the work already happening there.

So that function also appends a row to `.pd-pages/word-review-counts.jsonl`:

```json
{"page_index": 7, "content_hash": "…", "total_words": 345, "validated_words": 290}
```

**The row is appended only after the page's head is durably saved.** The same
function can fail to write the aggregate after the content blob exists, which the
routes surface as a 503. A row written before that would name a hash that never
became the page's head. So the append happens where the function already returns
its content hash, after the save succeeded.

**And the append is itself best effort.** It sits in its own try and except,
logged at warning and swallowed. The caller wraps this whole function in the
handling that produces a 503. Without that safety net, an unwritable journal
would report a saved edit as failed and invite a person to retry something that
already landed. A missing row makes a count say it did not see that page, which
the response already has a way to say.

**The content hash is what makes the row trustworthy.** A row whose hash does not
match the page's current head is stale, and that is detectable without opening
the page. A page that has never been saved has no row, which is honest: nobody
has touched it.

**Every mutation appends a row, and the reader keeps only the newest one per
page.** Every mutation goes through this function, not only a change to a
word's validated state, so a rebox or a region edit appends a row too. The
reader makes one pass and keeps the newest row for each page, exactly as the
region and page-kind journals are read today.

**The journal stays small.** A row is about 100 bytes, so a thousand saves cost
about 100 KB.

**Compaction happens on read, when the file holds more than ten rows per page of
the book.** At that point the reader has already built the newest row for each
page, so it writes those rows back and nothing more is needed. Ten times is
generous enough that an ordinary session never triggers it and small enough that
the file cannot grow indefinitely.

This one journal makes both remaining kinds countable. Words are the
subtraction. Typography's numerator was already journal-cheap; its denominator is
the total this row carries.

## One route, in the order the work happens

`GET /api/projects/{project_id}/review-queue` returns one entry per kind:

```json
{
  "kinds": [
    {"kind": "page_kind", "outstanding": 40, "total": 80, "available": true,
     "blocked_by": null, "first_page_index": 3},
    {"kind": "region", "outstanding": 12, "total": 29, "available": true,
     "blocked_by": null, "first_page_index": 5},
    {"kind": "word", "outstanding": 1204, "total": 18463, "available": true,
     "blocked_by": null, "first_page_index": 0, "pages_not_counted": 6},
    {"kind": "typography", "outstanding": 18463, "total": 18463,
     "available": true, "blocked_by": "word", "first_page_index": 0,
     "is_lower_bound": true},
    {"kind": "glyph", "outstanding": 0, "total": 0, "available": false,
     "blocked_by": null, "unavailable_reason": "no glyph predictor is wired"}
  ]
}
```

**The order is the order the work has to happen**, and it is not a preference.
Typography completion requires every word text-validated, and export requires
that too. So: words before typography before export. Glyphs sit outside the
chain.

**Regions depend on page kinds being proposed, not reviewed.** A region run
skips a page only when it has neither a proposed nor a confirmed kind. The
page-kind kind counts pages a person has not confirmed, which is a stricter
test. So region work is often available while page kinds still report
outstanding work.

**The exact gate: `blocked_by` for regions is set only when no page in the book
has either a proposed or a confirmed kind.** A single page confirmed by hand is
enough to unblock region work, with no proposal run needed at all.

**`blocked_by` is live, not a fixed label.** It names a kind that is genuinely
stopping this one right now, and it is null once that is no longer true. The
SPA picks the first kind in the returned order that has outstanding work and
no `blocked_by`. A kind with work but a `blocked_by` value is shown with what
it is waiting for, instead of as the thing to do next.

**A count that may understate says so in the response, not only in prose.**
Any kind whose number could be lower than the truth carries `is_lower_bound`.
Typography always does, because its staleness check is skipped. The word kind
does whenever `pages_not_counted` is above zero, which says how many pages had no
counts row to read. One field answers "can I trust this as complete", and the
other says why not, so a caller checking a single field is never misled.

**A kind that cannot be answered says so** rather than reporting zero. Glyphs
report `available: false` with a reason today. If a page has no counts row, the
word kind reports what it knows and names how many pages it could not see, so a
partial answer is never mistaken for a complete one.

**The route stays one read per journal.** Six journals live under `.pd-pages/`;
this route reads the ones it needs once each, exactly as the region queue does,
and opens no page.

## How the SPA uses the new route

The rail badge stops being a region count. It becomes the outstanding count for
the first kind that has work, and names that kind. The Queue drawer tab grows a
kind selector, defaulting to that same kind. `[` and `]` keep working on the
selected kind.

A kind blocked by another says what it is waiting for, rather than showing zero
and looking finished.

## What this does not build

- **Per-kind item lists for words and typography.** The route answers counts and
  where to start. Listing every outstanding word across a book is a different
  shape and nobody has asked for it.
- **A glyph predictor.** Until one exists, that kind reports unavailable. Task 10
  of the glyph plan owns it.
- **Backfilling counts for pages never saved by this version.** A page with no
  row is reported as unseen, not as zero work. A book becomes fully countable as
  its pages are saved.
- **Typography's per-head staleness check.** Its denominator now comes from the
  counts row. But the check that decides whether a correction is still current
  re-hashes the page image per head, and that check is uncached. The export
  path already loops that per page.

  Skipping it has a direction, and it is the unsafe one. A correction that has
  gone stale counts as reviewed here, where the real completion rule counts it
  as outstanding. So this count is a floor: the true remaining work is at least
  this much and may be more. A person could see zero outstanding while stale
  corrections still need rework. The route must label the typography count as a
  lower bound, and the SPA must not present it as completion. Making it exact
  means caching that staleness check, which is its own increment.

## Related

- [Book review queue](2026-09-17-book-review-queue-design.md) — the region-only
  route this generalizes.
- [Page-kind review](2026-09-17-page-kind-review-design.md) — the second kind.
- [Labeling track roadmap](../plans/2026-09-07-labeling-track-roadmap.md) —
  slice 5's goals.
