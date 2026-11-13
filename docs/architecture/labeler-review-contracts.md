# Labeler proposal review and queue contracts

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Owner:** CT
- **Created:** 2026-11-13
- **Last verified:** 2026-11-13
- **Provenance:** promoted from the implemented geometry, region-review, page-kind, and unified-queue
  increments after fresh source/test inspection and independent post-implementation review.
- **Disposition:** Current sibling-labeler behavior, not a synthetic-renderer integration or an approval of open policies.

The labeler separates proposed regions from human decisions and exposes review queues over both.
These contracts belong to `pdomain-ocr-labeler-spa`; this renderer has no runtime dependency on that implementation.
The [measurement boundary](measurement-and-labeling.md) records their shared context.

## Geometry proposals and the region surface

A proposal run measures and fits the book inside the worker rather than trusting persisted measurement as current.
The detector seam can carry measurements and optionally fit the book before proposing page regions.
Page reads use verified leases. Skipped pages are logged and mapped back to explicit page indexes.

Furniture detection can emit separate running-head and folio proposals.
Empty furniture bands produce no proposal.
Book-fitted splitting uses Otsu on pooled gaps, with the fixed share retained as a fallback.
Bottom furniture and braced groups are outside the bounded first increment.

The region surface adds a region rail target and region-only hit testing.
The smallest containing region wins; an undecided proposal takes precedence when areas tie.
The panel exposes role, confidence, evidence, and staleness.
Role overrides and accept/reject dispositions remain different actions.
Proposal jobs report terminal skip explanations.
Queue advancement follows the returned decision response rather than assuming every request succeeded.

Later region drawing, resizing, and word-membership editing also ship.
That does not implement the separate general matcher or sibling-membership invariant.

## Page-kind review and durable confirmation

The page payload can include the latest kind proposal, confirmed kind, and reviewed marker.
The book list reads each journal once rather than once per page.
Bulk confirmation returns per-page results and does not run OCR; the interface sends batches of 25 pages.
A withdrawn marker is unreviewed, while legacy stored kinds remain visible.
Confirmation requires durable storage and restores prior kind and generation when persistence fails.
Kind survives re-OCR and rotation.

Page kinds participate in the unified review queue.
This supersedes the earlier exclusion from the book queue without claiming kind-conditioned detectors or
a new kind-editing keyboard flow.

The remaining store-less-save policy is in
[Page-kind persistence](measurement-and-labeling.md#page-kind-persistence-and-the-remaining-storage-policy).

## Unified counts have explicit availability and freshness limits

The unified queue orders review kinds and reports live blocking prerequisites.
An unavailable kind differs from a kind with zero remaining items.
Book counts and bounded item lists serve different purposes; a count is not a cross-book list of every review item.

Typography uses per-page rollups, replacing the earlier 512 KiB read ceiling.
Counts can still be lower bounds.
Word-count rows include content hashes, but the queue does not compare them with live page heads.
Rows therefore do not prove freshness after every external mutation, and untouched pages are not backfilled.
Glyph prediction remains unavailable.
Word and typography counts do not imply cross-book item-list implementations.

These limitations preserve the distinction between cheap queue reads and an exact scan of all current page content.

## Book-level region decisions retain an open policy boundary

The region queue shares the resolver's undecided predicate.
Page summaries cover the book while returned items are bounded and ordered.
Proposal and decision journals are read once per request.
Navigation remains user-controlled and keeps its selection intent across queue updates.

Carry-forward matches by role and overlap, using the seed IoU threshold of 0.7.
It preserves the original human decision's provenance.
That matcher is not the general matcher proposed by the unfinished membership plan.

Current code also carries real human rejections and leaves hand-drawn overlaps undecided.
The original book-queue design deferred these policies.
This migration records the implementation but does not ratify either policy.
The owner choices remain in the [intent map](../context/intent-map.md), and the book-queue design remains partial.

## Evidence

- Code: `pdomain-ocr-labeler-spa` at `d4c7daa5`, `api/regions.py`, `api/page_kinds.py`,
  `api/pages.py`, `api/review_queue.py`, `core/regions/`, the proposal-job handlers,
  `core/typography_review_counts.py`, `core/word_review_counts.py`, and frontend review hooks/panels.
- Tests: sibling `tests/integration/test_regions_router.py`, `test_page_kinds_router.py`,
  `tests/unit/test_propose_regions_carry_match.py`, region detector tests, and
  `tests/e2e/test_review_queue_navigation.py`, `test_review_queue_panel.py`, and `test_page_kind_review.py`.
- Review: 2026-11-13 fresh independent post-implementation review of the five source designs, source, and tests.
  Stale descriptions were corrected; the two book-region policy choices remain unresolved.
- Verification: source and test inspection only. No sibling suite, browser session, or image review ran in this migration.
