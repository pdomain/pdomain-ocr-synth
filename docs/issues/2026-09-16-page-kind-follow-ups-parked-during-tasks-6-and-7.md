---
Status: active
Owner: CT
Created: 2026-09-16
Last verified: 2026-09-16
Kind: issue
Level: I1
---

# Four page-kind defects were parked during Tasks 6 and 7, and one blocks any UI

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-09-16
- **Resolution:** Open
- **Severity:** Medium — one item blocks every page-kind UI, one can measure
  unpinned image bytes on a book-labeling project, two are latent
- **Affected version:** `pdomain-ocr-labeler-spa` at `a64be5c`, the merge of
  `feature/page-kind-job`
- **Read when:** wiring `page_kind` into the page payload, building the
  page-kind review surface, touching `propose_page_kinds`, or changing the
  confirm route's failure paths
- **Search terms:** page_kind, propose_page_kinds, PageKindReviewedStore,
  store_unavailable, store_persist_failed, labeling_image_path,
  has_book_labeling_session, `_page_payload`

Tasks 6 and 7 of the [page-kind plan](../plans/2026-09-08-page-kind-end-to-end.md)
shipped and merged. Four findings were deliberately parked rather than fixed.
This file is where they live now, because the execution ledger that recorded
them was deleted with the plan's workspace.

## The confirmed kind never reaches a plain GET, so no UI can show it

`_page_payload` does not carry `page_kind` or `page_kind_reviewed`. The confirm
route attaches both to its own response through `model_copy` onto
`PagePayload.extra`, and nothing else reads `Page.page_kind` or
`PageKindReviewedStore`. Confirm a kind, reload the page, and the value is gone
from the response.

This was parked because the plan's own "What this plan does not do" section
names the payload wiring as a deliberate follow-up. That deferral is now the
thing standing between this backend and any review surface. Do it first.

The fix is to populate `page_kind` and `page_kind_reviewed` as typed fields on
`_page_payload`, the way `regions` and `proposals` already are, rather than
leaving them in the untyped `extra` dict.

## A run on a book-labeling project can measure bytes the manifest never pinned

`propose_page_kinds` reads `project.image_paths` directly. It does not go
through `ProjectState.labeling_image_path`, which exists to force lease-verified
image bytes, and it has no `has_book_labeling_session` guard of the kind
`core/jobs/handlers/auto_rotate_all.py:142` carries.

On a book-labeling project the run therefore reads raw on-disk images, bypassing
the manifest hash pin. Proposals can be measured from bytes the manifest did not
authorize.

This was parked because choosing between refusing the run, taking a lease, and
measuring unpinned bytes is a design decision rather than a small edit. Settle
that first, then implement.

## The book guard reads an untyped payload key instead of the typed field

`propose_page_kinds` re-checks the submitted project against the loaded one, so
a run started for book A cannot write durable proposals into book B's journal
after an intervening load. That guard reads `job.payload.get("project_id")`,
which is untyped, and silently does nothing when the key is missing or is not a
string. `Job.project_id` is a typed `str | None` set by the same `runner.submit`
call in `api/projects.py`.

Nothing can trigger this today, because the start route is the only submitter
and it sets both. A second submitter that omitted the payload key would get no
guard at all.

The fix is one line: guard on `job.project_id`, falling back to the payload only
when it is absent.

## A confirm that fails to persist leaves the kind set in memory

When `save_page_content_to_store` raises, the confirm route returns 503
`store_persist_failed` and writes no reviewed marker, which is correct. But
`page.page_kind` and the bumped `pstate.generation` both survive the failure. If
some later route persists that same `Page` object, the store ends up holding a
human-set `page_kind` with no matching marker.

That is the inverse of the invariant the final review's fix wave restored: the
marker can no longer claim a persistence that did not happen, but a persistence
can still happen with no marker.

The consequence is a page that a person confirmed showing up as unreviewed, so
they confirm it twice. The fix is either to restore the prior `page_kind` and
generation before returning 503, or to state in the route's docstring that this
direction is tolerated and why.

## Two smaller items, not worth their own section

- `core/page_kind/reviewed_store.py`'s module docstring still says the confirm
  route diffs the human's answer against `latest_proposal_for_page`. It does
  not, and never has. The same wrong claim was corrected in
  `core/page_kind/proposal_log.py` during the fix wave; this copy was missed.
- `propose_page_kinds` reports progress with `total` taken from
  `project.total_pages` while its loop walks `project.image_paths`. Only the
  durable `PageKindProposalRun.page_count` was reconciled to
  `len(classifications)`. A persisted envelope where the two disagree gives a
  wrong progress denominator.

## Also worth deciding: store-less mode is now inconsistent

The confirm route is the first mutation route in `api/pages.py` that requires
the event store rather than degrading without it. `save_page` still treats
`store is None` as a clean in-memory save.

That asymmetry is deliberate here, because a reviewed marker must never record a
confirmation that did not reach durable storage. But it means that with no store
wired, every other mutation route appears to work and this one always returns
503. Either `save_page` should refuse too, or the interface should hide confirm
when no store is present.

## Related

- [Page kind, end to end](../plans/2026-09-08-page-kind-end-to-end.md) — the
  plan these tasks carried out, now carrying five inline corrections that
  execution found in it.
- [Annotation provenance and persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md)
  — the design the plan argues from, and the authority for the persistence
  invariant the first and fourth items above bear on.
