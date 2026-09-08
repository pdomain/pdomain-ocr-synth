# Region Routes and Proposal Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the labeler eight REST routes over the region stores, plus a book-scoped background
job that fills the proposal store, so a person or an agent can create, edit, delete, and decide
regions over HTTP the day this lands, before any region UI exists.

**Architecture:** Confirmed regions are `Block` objects already living in the page's `Page.items`
tree, marked as regions by an opaque `region_id` in `Block.additional_block_attributes` — the same
free-form dict `Block.to_dict`/`from_dict` already round-trips. A new adapter walks that tree and
lifts marked blocks into `ResolvedRegion`. Every mutating route follows the convention already used
by 89 shipped routes: resolve, hold the per-page lock, mutate, bump `PageState.generation`, persist
via `save_page_content_to_store`, return the full `PagePayload`. Proposals and decisions never touch
the page blob — they live in the two JSONL journals the prior plan built. A new `propose_regions` job
type writes to those journals from a book-scoped background job, following the existing `JobRunner`
`_HANDLERS` pattern; it computes nothing itself in this plan (a pluggable, swappable detector,
defaulting to one that proposes nothing, stands in for the real geometry engine slice 4 builds).

**Tech Stack:** Python 3.13, FastAPI, pydantic, pytest, ruff, basedpyright, Playwright, React/Konva.

**Spec:** [Annotation provenance and
persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md).

## Agent Index

- **Kind:** plan
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-08
- **Last verified:** 2026-09-08
- **Provenance:** authored 2026-09-08 from the design above and direct inspection of
  `pdomain-ocr-labeler-spa` `bootstrap.py`, `api/words.py`, `api/pages.py`, `api/projects.py`,
  `api/refine.py`, `api/dependencies.py`, `core/jobs/runner.py`,
  `core/jobs/handlers/save_project.py`, `core/project_state.py`,
  `core/persistence/page_store.py`, its Makefile, `pyproject.toml`, `.github/workflows/ci.yml`,
  `tests/conformance/`, `tests/integration/conftest.py`, `tests/e2e/test_image_click_selection.py`,
  and `frontend/src/components/BBoxOverlay.tsx` and `PageImageCanvas.tsx`; and of
  `pdomain-book-tools` `pdomain_book_tools/ocr/block.py`, `ocr/page.py`,
  `ocr/reorganize_page_utils.py`, and `pdomain-book-contracts`
  `pdomain_book_contracts/geometry/bounding_box.py`
- **Disposition:** Active. Second half of slice 2 of the labeling track. Builds directly on the
  stores plan.
- **Read when:** implementing a region route, the proposal-run job, the `Block` adapter, or the
  frontend region layer.
- **Search terms:** region routes, propose_regions job, region_id, additional_block_attributes,
  confirmed_regions_from_page, operation_id, openapi-drift, block canvas, regions-confirmed,
  regions-proposed.

## Global Constraints

- Python floor is `>=3.13,<3.14`. Warnings are errors (`filterwarnings = ["error", ...]` in
  `pyproject.toml`) — this bites `Page(items=...)`, which is a deprecated constructor alias that
  raises `DeprecationWarning`; always construct a `Page` with `Page(blocks=[...])` or
  `Page.from_dict(...)`.
- Run any target with `AI=1` to capture verbose output to `.ci-ai.log`, e.g. `make AI=1 test`. Run
  `make AI=1 ci` before committing.
- **`RegionRole` and `KnowledgeState`** come from `pdomain_book_contracts.annotation` and must
  already be released (the annotation-vocabularies plan) before Task 1 starts.
- **`RegionProposal`, `ProposalRun`, `RegionDecision`, `Disposition`, `ResolvedRegion`,
  `RegionProposalLog`, `RegionDecisionLog`, `resolve_regions`** come from
  `pdomain_ocr_labeler_spa.core.regions` and must already be released (the stores-and-resolver plan)
  before Task 1 starts. Consume their exact signatures; do not redefine them. In particular,
  `ProposalRun.page_facet_digests: dict[int, dict[str, str]]` and `.depends_on: frozenset[str]`
  replace a single whole-page hash, and `resolve_regions` takes `runs: Mapping[str, ProposalRun]`
  plus a required `current_facet_digests: Mapping[str, str]` keyword — every call site and every
  `ProposalRun(...)` construction in this plan uses those, not the earlier
  `page_content_hashes: dict[int, str]` shape.
- **`PageKindProposalLog` and `PageKindReviewedStore`** come from
  `pdomain_ocr_labeler_spa.core.page_kind` and must already be released (the page-kind-end-to-end
  plan) before Task 5 starts. The `propose_regions` job handler reads page-kind state through
  these — see Task 5.
- **The page blob is only ever written by a human action.** The `propose_regions` job handler must
  never call `save_page_content_to_store` or `save_page_to_store`. Only the accept-proposal route
  (a human clicking or an agent calling on the human's behalf) writes the page blob among the new
  routes in this plan.
- **`Block.ALLOWED_BLOCK_ROLE_LABELS` in `pdomain-book-tools` still only has the original 20 role
  strings.** Neither the annotation-vocabularies plan nor the annotation-preconditions plan widens
  it to the full 34-value `RegionRole` vocabulary — both explicitly say so. Constructing or editing
  a `Block` with one of the 14 new roles (`catchword`, `signature mark`, `press figure`, `rule`,
  `brace`, `bracket`, `group label`, `plate`, `speaker label`, `stage direction`,
  `interlinear gloss`, `abandoned`, `decorated initial`, `unknown`) raises `ValueError` from
  `Block._normalize_label` **today**, in a different repo, outside this plan's scope. Every route
  that sets `block_role_labels` must catch that `ValueError` and return `400 invalid_region_role`
  rather than a 500. This is a real, tracked cross-repo gap, not a bug in this plan.
- **A region's box is not its membership.** `Block.add_item`/`Block.remove_item` call
  `self.recompute_bounding_box()`, which overwrites `bounding_box` from the union of the block's
  items. The membership route must save the region's box before mutating items and restore it
  after, or a membership edit silently resizes the region to fit its words.
- **Regions nest.** The vocabulary spec's hierarchy rules require it (rule 1: containment by
  nesting; rule 6: a `BlockCategory.GROUP` holding a `brace`/`bracket` plus a `group label`), and a
  region created with `child_type=BlockChildType.WORDS` raises `TypeError` when a `Block` is added
  to it (verified against `pdomain_book_tools/ocr/block.py`'s `add_item`) — a flat WORDS-only region
  cannot hold a nested region no matter what the route does. `create_region` therefore accepts an
  explicit `child_type` (`"words"`, the default, for a leaf region that holds words directly; or
  `"blocks"` for a nesting-capable container) and an optional `parent_region_id` to create a region
  as a child of an existing container region. `BlockCategory` still has only `BLOCK`, `PARAGRAPH`,
  and `LINE` — no `GROUP` — so the `brace`/`bracket`/`group label`/`page header` roles that need a
  `GROUP` category are still out of reach here; that gap is a dependency on the preconditions plan
  (`2026-09-08-annotation-preconditions-in-book-tools-and-measure.md`), not something this plan
  invents. Editing or deleting a container region does not cascade to its nested child regions
  (see "What this plan does not do").
- `make test` runs `uv run pytest tests/ -v --ignore=tests/e2e -m "not slow and not integration" -n
  auto`. Files under `tests/integration/` are not auto-marked; only tests explicitly decorated
  `@pytest.mark.integration` are excluded, so the `TestClient`-based route tests in this plan run
  under plain `make test`.
- `frontend/src/api/types.ts` is committed; `frontend/openapi.json` is gitignored. The
  `openapi-drift` CI job runs `make openapi-export` and fails the build if `types.ts` differs from
  what is committed. Every task that adds a route must run `make openapi-export` and commit the
  regenerated `types.ts`.

---

## File Structure

| file | responsibility |
| --- | --- |
| `src/pdomain_ocr_labeler_spa/core/regions/block_adapter.py` | `confirmed_regions_from_page`, `find_region_block`, `compute_page_facet_digests` |
| `src/pdomain_ocr_labeler_spa/core/models.py` | modified: `RegionView`, `RegionProposalView` added |
| `src/pdomain_ocr_labeler_spa/api/pages.py` | modified: `PagePayload.regions`/`.proposals`, `_page_payload` wiring |
| `src/pdomain_ocr_labeler_spa/api/regions.py` | new router: all 8 region/proposal routes |
| `src/pdomain_ocr_labeler_spa/bootstrap.py` | modified: `install_regions_router(app)` wired in |
| `src/pdomain_ocr_labeler_spa/core/jobs/handlers/propose_regions.py` | the `propose_regions` job handler |
| `src/pdomain_ocr_labeler_spa/core/jobs/runner.py` | modified: `_handle_propose_regions`, `_HANDLERS` entry |
| `frontend/src/components/BBoxOverlay.tsx` | modified: `regions-confirmed`/`regions-proposed` layers |
| `frontend/src/components/PageImageCanvas.tsx` | modified: region overlay items wired from `page.regions` |
| `frontend/src/api/types.ts`, `frontend/openapi.json` | regenerated via `make openapi-export` |
| `tests/unit/core/regions/test_block_adapter.py` | adapter round-trip and nesting |
| `tests/integration/test_regions_router.py` | CRUD + membership route tests |
| `tests/integration/test_region_proposals_router.py` | list/accept/reject + job route tests |
| `tests/conformance/test_region_block_round_trip.py` | golden fixture: role labels + sort order round-trip |
| `tests/e2e/test_region_layer_visibility.py` | Playwright: proposals render visibly distinct from confirmed |

---

### Task 1: Region and proposal views, the `Block` adapter, and `PagePayload` wiring

The adapter is the one piece of new work every route depends on: it is what turns a `Block` marked
as a region back into a `ResolvedRegion`, and it is how `_page_payload` learns to populate
`.regions` and `.proposals` on every response.

**Files:**

- Create: `src/pdomain_ocr_labeler_spa/core/regions/block_adapter.py`
- Modify: `src/pdomain_ocr_labeler_spa/core/models.py`
- Modify: `src/pdomain_ocr_labeler_spa/api/pages.py`
- Test: `tests/unit/core/regions/test_block_adapter.py`

**Interfaces:**

- Consumes: `ResolvedRegion`, `RegionProposal`, `RegionDecision`, `ProposalRun`, `Disposition`,
  `RegionProposalLog`, `RegionDecisionLog`, `resolve_regions` from the
  `pdomain_ocr_labeler_spa.core.regions` submodules (`.models`, `.proposal_log`, `.decision_log`,
  `.resolver` — the package `__init__.py` re-exports nothing);
  `RegionRole` from `pdomain_book_contracts.annotation`;
  `Block`, `Page`, `Word` from `pdomain_book_tools.ocr`.

- Produces: `confirmed_regions_from_page(page: Page) -> list[ResolvedRegion]`,
  `find_region_block(page: Page, region_id: str) -> Block | None`,
  `compute_page_facet_digests(page: Page, *, image_digest: str | None) -> dict[str, str]`,
  `RegionView`, `RegionProposalView`, and `PagePayload.regions: list[RegionView]` /
  `PagePayload.proposals: list[RegionProposalView]`.

- [ ] **Step 1: Write the failing adapter test**

```python
# tests/unit/core/regions/test_block_adapter.py
"""Unit tests for lifting confirmed Block regions off a page."""

from __future__ import annotations


def _region_block(region_id: str, role: str, ltrb: tuple[int, int, int, int]):
    from pdomain_book_contracts.geometry.bounding_box import BoundingBox
    from pdomain_book_tools.ocr.block import Block, BlockCategory, BlockChildType

    left, top, right, bottom = ltrb
    return Block(
        items=[],
        bounding_box=BoundingBox.from_ltrb(left, top, right, bottom, is_normalized=False),
        child_type=BlockChildType.WORDS,
        block_category=BlockCategory.BLOCK,
        block_role_labels=[role],
        additional_block_attributes={"region_id": region_id},
    )


def _plain_paragraph():
    from pdomain_book_contracts.geometry.bounding_box import BoundingBox
    from pdomain_book_tools.ocr.block import Block, BlockCategory, BlockChildType

    line = Block(
        items=[],
        bounding_box=BoundingBox.from_ltrb(0, 0, 10, 10, is_normalized=False),
        child_type=BlockChildType.WORDS,
        block_category=BlockCategory.LINE,
    )
    return Block(
        items=[line],
        bounding_box=BoundingBox.from_ltrb(0, 0, 10, 10, is_normalized=False),
        child_type=BlockChildType.BLOCKS,
        block_category=BlockCategory.PARAGRAPH,
    )


def test_a_region_block_lifts_into_a_confirmed_resolved_region() -> None:
    from pdomain_book_contracts.annotation import RegionRole
    from pdomain_book_tools.ocr.page import Page

    from pdomain_ocr_labeler_spa.core.regions.block_adapter import confirmed_regions_from_page

    page = Page(width=200, height=300, page_index=0, blocks=[_region_block("r1", "poetry", (10, 20, 100, 200))])
    resolved = confirmed_regions_from_page(page)

    assert len(resolved) == 1
    assert resolved[0].region_id == "r1"
    assert resolved[0].role is RegionRole.POETRY
    assert resolved[0].confirmed is True
    assert resolved[0].confidence is None
    assert resolved[0].box == (10, 20, 100, 200)


def test_a_plain_paragraph_with_no_region_id_is_not_a_region() -> None:
    from pdomain_book_tools.ocr.page import Page

    from pdomain_ocr_labeler_spa.core.regions.block_adapter import confirmed_regions_from_page

    page = Page(width=200, height=300, page_index=0, blocks=[_plain_paragraph()])
    assert confirmed_regions_from_page(page) == []


def test_nested_regions_are_both_found_and_addressable() -> None:
    from pdomain_book_contracts.geometry.bounding_box import BoundingBox
    from pdomain_book_tools.ocr.block import Block, BlockCategory, BlockChildType
    from pdomain_book_tools.ocr.page import Page

    from pdomain_ocr_labeler_spa.core.regions.block_adapter import (
        confirmed_regions_from_page,
        find_region_block,
    )

    inner = _region_block("inner", "caption", (30, 30, 40, 40))
    outer = Block(
        items=[inner],
        bounding_box=BoundingBox.from_ltrb(10, 10, 100, 100, is_normalized=False),
        child_type=BlockChildType.BLOCKS,
        block_category=BlockCategory.BLOCK,
        block_role_labels=["figure"],
        additional_block_attributes={"region_id": "outer"},
    )
    page = Page(width=200, height=300, page_index=0, blocks=[outer])

    ids = {r.region_id for r in confirmed_regions_from_page(page)}
    assert ids == {"outer", "inner"}
    assert find_region_block(page, "inner") is inner
    assert find_region_block(page, "missing-id") is None


def test_a_block_with_an_unrecognised_role_string_is_skipped_not_raised() -> None:
    from pdomain_book_tools.ocr.page import Page

    from pdomain_ocr_labeler_spa.core.regions.block_adapter import confirmed_regions_from_page

    stale = _region_block("r1", "poetry", (0, 0, 10, 10))
    stale.block_role_labels = ["some-future-role-not-yet-in-region-role"]
    page = Page(width=200, height=300, page_index=0, blocks=[stale])
    assert confirmed_regions_from_page(page) == []


def test_a_confirmed_region_surfaces_its_member_word_signatures() -> None:
    from pdomain_book_contracts.geometry.bounding_box import BoundingBox
    from pdomain_book_tools.ocr.page import Page
    from pdomain_book_tools.ocr.word import Word

    from pdomain_ocr_labeler_spa.core.regions.block_adapter import confirmed_regions_from_page

    word = Word(text="verse", bounding_box=BoundingBox.from_ltrb(12, 22, 40, 38, is_normalized=False))
    region = _region_block("r1", "poetry", (10, 20, 100, 200))
    region.add_item(word)
    page = Page(width=200, height=300, page_index=0, blocks=[region])

    resolved = confirmed_regions_from_page(page)

    assert len(resolved) == 1
    assert resolved[0].member_word_signatures == (word.bbox_signature,)


def test_a_confirmed_region_surfaces_its_origin_proposal_id() -> None:
    from pdomain_book_tools.ocr.page import Page

    from pdomain_ocr_labeler_spa.core.regions.block_adapter import confirmed_regions_from_page

    promoted = _region_block("r1", "poetry", (10, 20, 100, 200))
    promoted.additional_block_attributes["source_proposal_id"] = "p1"
    page = Page(width=200, height=300, page_index=0, blocks=[promoted])

    resolved = confirmed_regions_from_page(page)

    assert resolved[0].proposal_id == "p1"


def test_a_confirmed_region_with_no_stamped_origin_surfaces_none() -> None:
    """A region blob written before this correction, or edited outside the routes."""
    from pdomain_book_tools.ocr.page import Page

    from pdomain_ocr_labeler_spa.core.regions.block_adapter import confirmed_regions_from_page

    unstamped = _region_block("r1", "poetry", (10, 20, 100, 200))
    page = Page(width=200, height=300, page_index=0, blocks=[unstamped])

    resolved = confirmed_regions_from_page(page)

    assert resolved[0].proposal_id is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/regions/test_block_adapter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named '...core.regions.block_adapter'`

- [ ] **Step 3: Write the adapter**

Create `src/pdomain_ocr_labeler_spa/core/regions/block_adapter.py`:

```python
"""Lift confirmed ``Block`` regions off a page into ``ResolvedRegion`` views.

A region is a ``Block`` carrying an explicit ``region_id`` in
``additional_block_attributes`` — the marker that a person created or edited it
through the region routes. A block with a role label but no ``region_id`` is
ordinary paragraph/line structure inherited from OCR or the reorganize
pipeline, not a region under this design. ``additional_block_attributes`` is a
plain ``dict[str, object]`` that ``Block.to_dict``/``from_dict`` already
round-trips, so no new storage is needed to carry it.

Also computes the four facet digests a ``ProposalRun`` names in ``depends_on``
and a caller compares against at read time (spec §"A proposal goes stale per
facet, not per page"). The digest algorithm lives here, alongside the adapter,
because both are read off the same live ``Page``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Sequence

from pdomain_book_contracts.annotation import RegionRole
from pdomain_book_tools.ocr.block import Block
from pdomain_book_tools.ocr.page import Page
from pdomain_book_tools.ocr.word import Word

from pdomain_ocr_labeler_spa.core.regions.models import ResolvedRegion

_REGION_ID_KEY = "region_id"
_SOURCE_PROPOSAL_ID_KEY = "source_proposal_id"


def _walk_blocks(items: Sequence[Word | Block]) -> Iterator[Block]:
    """Yield every ``Block`` reachable from ``items``, at any nesting depth."""
    for item in items:
        if isinstance(item, Block):
            yield item
            yield from _walk_blocks(item.items)


def find_region_block(page: Page, region_id: str) -> Block | None:
    """Return the ``Block`` carrying ``region_id`` anywhere on ``page``, or ``None``."""
    for block in _walk_blocks(page.items):
        if block.additional_block_attributes.get(_REGION_ID_KEY) == region_id:
            return block
    return None


def confirmed_regions_from_page(page: Page) -> list[ResolvedRegion]:
    """Every region a person confirmed on this page, as ``ResolvedRegion``.

    Skips blocks with no ``region_id`` (ordinary structure) and blocks whose
    first role label is not a recognised ``RegionRole`` value (defensive
    against a future role or a block edited outside this design) rather than
    raising — a page must always render, even with one malformed region.

    ``member_word_signatures`` is read straight off ``block.words`` (which
    recurses through a nesting-capable ``BLOCKS`` container the same as a
    leaf ``WORDS`` block) as stable bounding-box signatures — never a
    line/word ordinal. ``proposal_id`` surfaces whatever the routes stamped
    into ``source_proposal_id`` when the region was created or promoted: a
    real proposal id, the explicit hand-drawn sentinel, or ``None`` for a
    region blob written before this correction landed.
    """
    resolved: list[ResolvedRegion] = []
    for block in _walk_blocks(page.items):
        region_id = block.additional_block_attributes.get(_REGION_ID_KEY)
        if not isinstance(region_id, str) or not region_id:
            continue
        if not block.block_role_labels:
            continue
        try:
            role = RegionRole(block.block_role_labels[0])
        except ValueError:
            continue
        if block.bounding_box is None:
            continue
        left, top, right, bottom = block.bounding_box.to_ltrb()
        source_proposal_id = block.additional_block_attributes.get(_SOURCE_PROPOSAL_ID_KEY)
        member_signatures = tuple(
            sig for sig in (word.bbox_signature for word in block.words) if sig is not None
        )
        resolved.append(
            ResolvedRegion(
                role=role,
                box=(round(left), round(top), round(right), round(bottom)),
                confirmed=True,
                confidence=None,
                proposal_id=source_proposal_id if isinstance(source_proposal_id, str) else None,
                region_id=region_id,
                member_word_signatures=member_signatures,
            )
        )
    return resolved


def _digest_of(payload: object) -> str:
    """Deterministic sha256 hex digest of a JSON-serializable payload."""
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def compute_page_facet_digests(page: Page, *, image_digest: str | None) -> dict[str, str]:
    """Digest each of the four facets a proposal run can depend on.

    Recomputed from the live page rather than declared by a mutation route —
    spec §"Facet digests are computed, never declared" — so a change is
    caught no matter which route made it. ``image_digest`` is passed in
    rather than derived here: the block tree carries no reference to the
    source image blob, only the page's content-addressed provenance chain
    does (``ProvenanceNode.blob_refs[1]``, by the convention
    ``pdomain_ops.page_aggregate`` documents — index 0 is the page-content
    JSON, index 1 the source image; callers that only have index 0 pass that
    instead, since a stand-in digest still detects *some* image change).

    Word-box rows are serialized to strings and sorted as strings — not as
    raw signature tuples — because a signature's trailing ``is_normalized``
    field is ``bool | None``, and ``None``/``bool`` are not orderable.
    """
    word_box_rows = sorted(
        json.dumps(list(sig), default=str)
        for sig in (word.bbox_signature for word in page.words)
        if sig is not None
    )
    word_boxes = _digest_of(word_box_rows)
    line_structure = _digest_of(
        [
            [
                line.block_category.value if line.block_category is not None else None,
                line.override_page_sort_order,
            ]
            for line in page.lines
        ]
    )
    word_text = _digest_of([[word.text, word.ground_truth_text] for word in page.words])
    return {
        "word_boxes": word_boxes,
        "line_structure": line_structure,
        "page_image": image_digest or "",
        "word_text": word_text,
    }


__all__ = ["compute_page_facet_digests", "confirmed_regions_from_page", "find_region_block"]
```

- [ ] **Step 4: Run the adapter tests**

Run: `uv run pytest tests/unit/core/regions/test_block_adapter.py -v`
Expected: PASS, all seven tests.

- [ ] **Step 5: Add the wire-shape views to `core/models.py`**

Read `src/pdomain_ocr_labeler_spa/core/models.py` first (the file already defines `BBox`,
`LineFilter`, `Selection`, and similar small wire models). Add, after the `BBox` class:

```python
class RegionView(BaseModel):
    """One resolved region as the labeler renders it — spec §"Reading order..." / resolver.

    ``confirmed=True`` means a person put it there; ``confirmed=False`` means it is a
    proposal above the labeler's display threshold (zero — the labeler shows everything
    and renders the two differently). ``region_id`` is set only when confirmed.
    ``proposal_id`` is set for an unconfirmed proposal (the proposal itself), and also for
    a confirmed region promoted from one (its origin) — an explicit hand-drawn sentinel
    when a person drew the region unprompted, or ``None`` when the origin was never
    stamped. ``member_word_signatures`` is populated for a confirmed region (bounding-box
    signatures, never a line/word ordinal); empty for a region resolved from a proposal,
    which carries no membership of its own. ``stale`` is only ever True for an unconfirmed
    proposal whose run read facets that have since changed on the page.
    """

    region_id: str | None = None
    proposal_id: str | None = None
    role: "RegionRole"
    box: BBox
    confirmed: bool
    confidence: float | None = None
    member_word_signatures: list[tuple[float, float, float, float, bool | None]] = Field(
        default_factory=list
    )
    stale: bool = False


class RegionProposalView(BaseModel):
    """One proposal as the labeler's proposal list shows it — role, confidence, evidence.

    ``disposition`` and ``decided_region_id`` are ``None`` until a person accepts or
    rejects the proposal; that is what distinguishes "nobody has looked yet" from
    "looked at and refused" once a decision is recorded.
    """

    proposal_id: str
    run_id: str
    page_index: int
    role: "RegionRole"
    box: BBox
    confidence: float
    evidence: dict[str, Any]
    disposition: str | None = None
    decided_region_id: str | None = None
```

Add the import near the top of the file, beside the other third-party imports:

```python
from pdomain_book_contracts.annotation import RegionRole
```

Replace the two `"RegionRole"` forward-reference strings above with a plain `RegionRole` reference
now that the import exists (they are written as strings above only to show where the import must
land relative to the classes; the committed file uses the real type, not a string).

- [ ] **Step 6: Wire `PagePayload` and `_page_payload` in `api/pages.py`**

Read `src/pdomain_ocr_labeler_spa/api/pages.py` first. In the `PagePayload` class, add two fields
after `history`:

```python
    regions: list[RegionView] = Field(default_factory=list)
    proposals: list[RegionProposalView] = Field(default_factory=list)
```

Add to the imports from `..core.models`:

```python
from ..core.models import EncodedDims, LineFilter, LineMatch, PageSource, RegionProposalView, RegionView, Selection
```

Add near the top-level imports:

```python
from ..core.regions.block_adapter import compute_page_facet_digests, confirmed_regions_from_page
from ..core.regions.decision_log import RegionDecisionLog
from ..core.regions.models import Disposition, ProposalRun, RegionProposal
from ..core.regions.proposal_log import RegionProposalLog
from ..core.regions.resolver import resolve_regions
```

Inside `_page_payload`, resolve the live `Page` for the region assembly with a real `isinstance`
check, immediately before the assembly block. Do **not** reuse the existing `is_page` /
`payload_obj` locals: `is_page` is `isinstance(payload_obj, _Page) or hasattr(payload_obj,
"lines")`, and that `hasattr` arm is true for the duck-typed test stubs this file already carries
(`_StubPage` in `tests/unit/api/test_b1_b3_f1.py` exposes `.lines` and `.paragraphs` but no
`.items`), so handing `payload_obj` to `confirmed_regions_from_page` raises `AttributeError` at
runtime. The `or` also defeats `isinstance` narrowing, so `payload_obj` stays `object | None` and
fails typecheck. Both locals are bound inside a nested `if`, so they may not exist at all here.

```python
    # Region/proposal assembly. Only a genuine ``Page`` carries block
    # structure — the duck-typed test stubs some payloads use elsewhere in
    # this file expose ``.lines`` but not ``.items``/``.words``, so this is
    # gated on a real ``isinstance`` check rather than the looser duck-typed
    # ``is_page`` test used above for the line-matches path.
    _resolved_page_for_regions: Page | None = None
    if pstate is not None and pstate.page_record is not None:
        _raw_payload = pstate.page_record.payload
        if isinstance(_raw_payload, Page):
            _resolved_page_for_regions = _raw_payload
```

Immediately before `return PagePayload(`, add the region/proposal assembly. `page_store` is already
a parameter of `_page_payload` (confirmed against the live signature — `_page_payload(*, project_id,
page_index, project_state, settings, app_config=None, page_store=None)`); this is the only place
that carries a page's provenance chain, so the `page_image` facet digest is read here rather than
invented. Its `blob_refs` layout is not stable across every write path (the OCR-ingest path writes
`[content_hash, image_hash]`; the labeler-edit path writes `[content_hash]` alone), so a run that
recorded index 1 but is now compared against a page whose head only has index 0 falls back to
index 0 — a stand-in digest that still detects *some* image change is better than none:

```python
    regions: list[RegionView] = []
    proposals: list[RegionProposalView] = []
    if _resolved_page_for_regions is not None:
        image_digest: str | None = None
        if page_store is not None and pstate is not None and pstate.page_id is not None:
            try:
                agg_record = page_store.get_page(pstate.page_id).record
                head = agg_record.provenance.head if agg_record.provenance else None
                if head is not None and head.blob_refs:
                    image_digest = head.blob_refs[1] if len(head.blob_refs) > 1 else head.blob_refs[0]
            except Exception:  # pragma: no cover - defensive; a missing aggregate just skips the digest
                image_digest = None
        current_facet_digests = compute_page_facet_digests(
            _resolved_page_for_regions, image_digest=image_digest
        )

        confirmed = confirmed_regions_from_page(_resolved_page_for_regions)
        proposal_log = RegionProposalLog(project.project_root)
        decision_log = RegionDecisionLog(project.project_root)
        raw_proposals: list[RegionProposal] = proposal_log.proposals_for_page(page_index)
        runs: dict[str, ProposalRun] = {run.run_id: run for run in proposal_log.runs()}
        decisions = {
            p.proposal_id: decision_log.decision_for(p.proposal_id, run_id=p.run_id)
            for p in raw_proposals
        }
        live_decisions = {pid: d for pid, d in decisions.items() if d is not None}
        # threshold=0.0: the labeler shows every proposal and renders it visibly
        # differently from a confirmed region — the execution engine is the only
        # caller that ever passes a real threshold.
        resolved = resolve_regions(
            confirmed,
            raw_proposals,
            live_decisions,
            runs,
            threshold=0.0,
            current_facet_digests=current_facet_digests,
        )
        regions = [
            RegionView(
                region_id=r.region_id,
                proposal_id=r.proposal_id,
                role=r.role,
                box=BBox(x=r.box[0], y=r.box[1], width=r.box[2] - r.box[0], height=r.box[3] - r.box[1]),
                confirmed=r.confirmed,
                confidence=r.confidence,
                member_word_signatures=list(r.member_word_signatures),
                stale=r.stale,
            )
            for r in resolved
        ]
        # A loop, not a comprehension: `decisions[p.proposal_id]` is typed
        # `RegionDecision | None`, and a `decisions.get(...)` truthiness test in a
        # conditional expression does not narrow the separate subscript in its body.
        # basedpyright reports `reportOptionalMemberAccess` on both fields. Binding
        # `decision` once narrows correctly and halves the dict lookups.
        proposals = []
        for p in raw_proposals:
            decision = decisions.get(p.proposal_id)
            proposals.append(
                RegionProposalView(
                    proposal_id=p.proposal_id,
                    run_id=p.run_id,
                    page_index=p.page_index,
                    role=p.role,
                    box=BBox(x=p.box[0], y=p.box[1], width=p.box[2] - p.box[0], height=p.box[3] - p.box[1]),
                    confidence=p.confidence,
                    evidence=p.evidence,
                    disposition=decision.disposition.value if decision is not None else None,
                    decided_region_id=decision.region_id if decision is not None else None,
                )
            )
```

Then add `regions=regions, proposals=proposals` to the `PagePayload(...)` call.

`BBox` and `Disposition` must be imported too — add `BBox` to the `..core.models` import list above,
and confirm `Disposition` is imported (used only for its `.value` via the decision object, so the
explicit import can be dropped if unused — keep it only if a type annotation needs it).

- [ ] **Step 7: Run the unit and page-payload tests**

Run: `uv run pytest tests/unit/ -k "regions or page_payload" -v`
Expected: PASS. `_page_payload` callers with no project loaded, or a project whose page has no
`Page` object yet, must still return `regions=[]` and `proposals=[]` rather than raising — spot
check by running the full existing pages test file:

Run: `uv run pytest tests/unit/api/test_pages_get.py tests/unit/api/test_pages_image.py
tests/unit/api/test_b1_b3_f1.py tests/integration/test_pages_router.py -v`
Expected: PASS, no regressions. (There is no `tests/unit/api/test_pages.py`; `_page_payload` and
`GET /pages/{idx}` are covered by those four files. `test_b1_b3_f1.py` is the one that uses the
duck-typed `_StubPage`, so it is the targeted regression check for the `isinstance` gate above.)

- [ ] **Step 8: Regenerate the OpenAPI contract**

Run: `make openapi-export`

This task adds no route, but it does add two fields to `PagePayload`, which changes the OpenAPI
schema. Without this step the `openapi-drift` CI job is red from here until Task 3 regenerates
`types.ts` for its own route.

- [ ] **Step 9: Commit**

The subject below is 55 characters. `gitlint` rejects anything past 72, so keep detail in the body.

```bash
git add src/pdomain_ocr_labeler_spa/core/regions/block_adapter.py \
  src/pdomain_ocr_labeler_spa/core/models.py src/pdomain_ocr_labeler_spa/api/pages.py \
  tests/unit/core/regions/test_block_adapter.py frontend/src/api/types.ts
git commit -m "feat(regions): lift Block regions into PagePayload views"
```

---

### Task 2: Region CRUD routes — create, edit, delete

The first three of the eight routes. New router file, wired into `bootstrap.py` in this task since
every later task adds routes to the same file and needs the router already mounted.

**Files:**

- Create: `src/pdomain_ocr_labeler_spa/api/regions.py`
- Modify: `src/pdomain_ocr_labeler_spa/bootstrap.py`
- Test: `tests/integration/test_regions_router.py`

**Interfaces:**

- Consumes: `_check_project_and_page`, `_page_not_loaded`, `_resolve_page_object`,
  `_save_to_store_best_effort`, `_store_persist_failed_response`, `_refresh_payload_response` from
  `.words` (the established cross-module private-helper reuse pattern already used by `words.py`
  importing `_page_payload` from `.pages`); `find_region_block` from
  `..core.regions.block_adapter`; `build_recovered_words_block` from
  `pdomain_book_tools.ocr.reorganize_page_utils`.
- Produces: `POST .../regions` (`create_region`), `PATCH .../regions/{region_id}` (`edit_region`),
  `DELETE .../regions/{region_id}` (`delete_region`), each returning the full `PagePayload`.

- [ ] **Step 1: Write the failing integration test**

```python
# tests/integration/test_regions_router.py
"""Integration tests for ``api/regions.py`` — create, edit, delete, membership, proposals."""

from __future__ import annotations

from typing import Any

_BASE = "/api/projects/book1/pages/0"


def test_create_region_adds_a_confirmed_region_to_the_payload(toolbar_loaded: Any) -> None:
    client, _ps, _page = toolbar_loaded
    r = client.post(
        f"{_BASE}/regions",
        json={"role": "poetry", "box": {"x": 5, "y": 5, "width": 50, "height": 50}},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    regions = [reg for reg in body["regions"] if reg["confirmed"]]
    assert len(regions) == 1
    assert regions[0]["role"] == "poetry"
    assert regions[0]["box"] == {"x": 5, "y": 5, "width": 50, "height": 50}
    assert regions[0]["region_id"]


def test_create_region_with_an_unsupported_role_returns_400(toolbar_loaded: Any) -> None:
    client, _ps, _page = toolbar_loaded
    r = client.post(
        f"{_BASE}/regions",
        json={"role": "catchword", "box": {"x": 5, "y": 5, "width": 50, "height": 50}},
    )
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "invalid_region_role"


def test_edit_region_changes_role_and_box(toolbar_loaded: Any) -> None:
    client, _ps, _page = toolbar_loaded
    created = client.post(
        f"{_BASE}/regions",
        json={"role": "poetry", "box": {"x": 5, "y": 5, "width": 50, "height": 50}},
    ).json()
    region_id = next(reg["region_id"] for reg in created["regions"] if reg["confirmed"])

    r = client.patch(
        f"{_BASE}/regions/{region_id}",
        json={"role": "blockquote", "box": {"x": 10, "y": 10, "width": 20, "height": 20}},
    )
    assert r.status_code == 200, r.text
    region = next(reg for reg in r.json()["regions"] if reg["region_id"] == region_id)
    assert region["role"] == "blockquote"
    assert region["box"] == {"x": 10, "y": 10, "width": 20, "height": 20}


def test_edit_region_with_an_unsupported_role_returns_400(toolbar_loaded: Any) -> None:
    """A rejected role must never reach the blob — a later ``from_dict`` would fail to load it."""
    client, _ps, _page = toolbar_loaded
    created = client.post(
        f"{_BASE}/regions",
        json={"role": "poetry", "box": {"x": 5, "y": 5, "width": 50, "height": 50}},
    ).json()
    region_id = next(reg["region_id"] for reg in created["regions"] if reg["confirmed"])

    r = client.patch(f"{_BASE}/regions/{region_id}", json={"role": "catchword"})
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "invalid_region_role"

    # The rejection must never have reached the blob — the region still carries its
    # original role, proving nothing was mutated before the 400 was returned.
    payload = client.get(_BASE).json()
    region = next(reg for reg in payload["regions"] if reg["region_id"] == region_id)
    assert region["role"] == "poetry"


def test_edit_unknown_region_returns_404(toolbar_loaded: Any) -> None:
    client, _ps, _page = toolbar_loaded
    r = client.patch(f"{_BASE}/regions/does-not-exist", json={"role": "poetry"})
    assert r.status_code == 404, r.text
    assert r.json()["error"] == "region_not_found"


def test_delete_region_removes_it_from_the_payload(toolbar_loaded: Any) -> None:
    client, _ps, _page = toolbar_loaded
    created = client.post(
        f"{_BASE}/regions",
        json={"role": "poetry", "box": {"x": 5, "y": 5, "width": 50, "height": 50}},
    ).json()
    region_id = next(reg["region_id"] for reg in created["regions"] if reg["confirmed"])

    r = client.delete(f"{_BASE}/regions/{region_id}")
    assert r.status_code == 200, r.text
    assert all(reg["region_id"] != region_id for reg in r.json()["regions"])


def test_create_region_stamps_the_hand_drawn_sentinel_as_its_origin(toolbar_loaded: Any) -> None:
    """A person drawing a region unprompted, not accepting a proposal, is a distinct fact."""
    client, _ps, _page = toolbar_loaded
    r = client.post(
        f"{_BASE}/regions",
        json={"role": "poetry", "box": {"x": 5, "y": 5, "width": 50, "height": 50}},
    )
    assert r.status_code == 200, r.text
    region = next(reg for reg in r.json()["regions"] if reg["confirmed"])
    assert region["proposal_id"] == "hand-drawn"


def test_create_a_container_region_then_nest_a_child_under_it(toolbar_loaded: Any) -> None:
    client, _ps, page = toolbar_loaded
    container = client.post(
        f"{_BASE}/regions",
        json={
            "role": "figure",
            "box": {"x": 0, "y": 0, "width": 200, "height": 300},
            "child_type": "blocks",
        },
    ).json()
    parent_id = next(reg["region_id"] for reg in container["regions"] if reg["confirmed"])

    r = client.post(
        f"{_BASE}/regions",
        json={
            "role": "caption",
            "box": {"x": 10, "y": 10, "width": 20, "height": 20},
            "parent_region_id": parent_id,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    child_id = next(
        reg["region_id"] for reg in body["regions"] if reg["confirmed"] and reg["role"] == "caption"
    )

    from pdomain_ocr_labeler_spa.api.regions import find_region_block

    parent_block = find_region_block(page, parent_id)
    child_block = find_region_block(page, child_id)
    assert parent_block is not None and child_block is not None
    assert child_block in parent_block.items
    assert child_block not in page.items
    # The container keeps the box it was drawn with. Without the save/restore,
    # ``add_item``'s recompute shrinks it to the child's (10, 10, 30, 30).
    assert parent_block.bounding_box is not None
    assert parent_block.bounding_box.to_ltrb() == (0.0, 0.0, 200.0, 300.0)


def test_delete_nested_region_removes_it_from_its_parent_and_preserves_parent_box(
    toolbar_loaded: Any,
) -> None:
    """Exercises ``_region_owner``'s tree-walking branch, not just its ``return page``
    fallback — a region created with ``parent_region_id`` lives in the parent's
    ``items``, and deleting it must not let ``Block.remove_item``'s bounding-box
    recompute shrink the container to whatever it has left.
    """
    client, _ps, page = toolbar_loaded
    container = client.post(
        f"{_BASE}/regions",
        json={
            "role": "figure",
            "box": {"x": 0, "y": 0, "width": 200, "height": 300},
            "child_type": "blocks",
        },
    ).json()
    parent_id = next(reg["region_id"] for reg in container["regions"] if reg["confirmed"])

    nested = client.post(
        f"{_BASE}/regions",
        json={
            "role": "caption",
            "box": {"x": 10, "y": 10, "width": 20, "height": 20},
            "parent_region_id": parent_id,
        },
    ).json()
    child_id = next(
        reg["region_id"] for reg in nested["regions"] if reg["confirmed"] and reg["role"] == "caption"
    )

    from pdomain_ocr_labeler_spa.api.regions import find_region_block

    parent_block = find_region_block(page, parent_id)
    child_block = find_region_block(page, child_id)
    assert parent_block is not None and child_block is not None
    assert parent_block.bounding_box is not None
    original_parent_box = parent_block.bounding_box.to_ltrb()

    r = client.delete(f"{_BASE}/regions/{child_id}")
    assert r.status_code == 200, r.text
    assert all(reg["region_id"] != child_id for reg in r.json()["regions"])

    assert child_block not in parent_block.items
    assert find_region_block(page, child_id) is None
    assert parent_block.bounding_box is not None
    assert parent_block.bounding_box.to_ltrb() == original_parent_box


def test_nesting_under_a_non_container_parent_returns_400(toolbar_loaded: Any) -> None:
    client, _ps, _page = toolbar_loaded
    leaf = client.post(
        f"{_BASE}/regions",
        json={"role": "poetry", "box": {"x": 0, "y": 0, "width": 50, "height": 50}},
    ).json()
    leaf_id = next(reg["region_id"] for reg in leaf["regions"] if reg["confirmed"])

    r = client.post(
        f"{_BASE}/regions",
        json={"role": "caption", "box": {"x": 5, "y": 5, "width": 10, "height": 10}, "parent_region_id": leaf_id},
    )
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "parent_not_nesting_capable"


def test_nesting_under_an_unknown_parent_returns_404(toolbar_loaded: Any) -> None:
    client, _ps, _page = toolbar_loaded
    r = client.post(
        f"{_BASE}/regions",
        json={
            "role": "caption",
            "box": {"x": 5, "y": 5, "width": 10, "height": 10},
            "parent_region_id": "does-not-exist",
        },
    )
    assert r.status_code == 404, r.text
    assert r.json()["error"] == "region_not_found"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_regions_router.py -v`
Expected: FAIL — `404 Not Found` on every request (no route registered yet).

- [ ] **Step 3: Write the router**

Create `src/pdomain_ocr_labeler_spa/api/regions.py`:

```python
"""``/api/projects/{project_id}/pages/{page_index}/regions`` router.

Spec authority: ``docs/specs/2026-09-07-region-provenance-and-persistence-design.md``
"The routes follow the convention already in place". Every mutating route
resolves the page, holds the per-page lock, mutates, bumps
``PageState.generation``, persists via ``_save_to_store_best_effort``, and
returns the full ``PagePayload`` — the same shape ``api/words.py`` uses.

A region is a ``Block`` carrying an opaque ``region_id`` in
``additional_block_attributes``, and it nests: a leaf region (``child_type=
WORDS``) holds words directly and lives wherever it was created — as a
top-level ``Page.items`` sibling by default, or as a child of a
nesting-capable container region when ``parent_region_id`` is given. A
container region (``child_type=BLOCKS``) holds other regions and nothing
else — a ``WORDS``-typed block raises ``TypeError`` if a ``Block`` is added
to it, so a leaf region can never itself hold a nested child.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import JSONResponse
from pdomain_book_contracts.annotation import RegionRole
from pdomain_book_contracts.geometry.bounding_box import BoundingBox
from pdomain_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pdomain_book_tools.ocr.reorganize_page_utils import build_recovered_words_block
from pydantic import BaseModel

from ..core.models import BBox
from ..core.persistence.config_yaml import AppConfig
from ..core.persistence.page_store import LabelerPageStore
from ..core.project_state import ProjectState
from ..core.regions.block_adapter import find_region_block
from ..settings import Settings
from .dependencies import bind_page_labeling_lease, get_app_config, get_page_store_optional, get_project_state, get_settings
from .middleware.error_handler import ApiError
from .pages import PagePayload
from .words import (
    _check_project_and_page,
    _page_not_loaded,
    _refresh_payload_response,
    _resolve_page_object,
    _save_to_store_best_effort,
    _store_persist_failed_response,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["regions"])

_REGION_ID_KEY = "region_id"
_SOURCE_PROPOSAL_ID_KEY = "source_proposal_id"
_HAND_DRAWN_SENTINEL = "hand-drawn"


# ── Request models ─────────────────────────────────────────────────────


class CreateRegionRequest(BaseModel):
    """``child_type="blocks"`` creates a nesting-capable container region — one that
    can hold other regions but no words of its own. ``parent_region_id`` nests the new
    region as a child of an existing container region instead of adding it as a
    top-level ``Page.items`` sibling; the parent must itself be a container.
    """

    role: RegionRole
    box: BBox
    child_type: Literal["words", "blocks"] = "words"
    parent_region_id: str | None = None


class EditRegionRequest(BaseModel):
    role: RegionRole | None = None
    box: BBox | None = None


# ── Shared helpers ───────────────────────────────────────────────────────


def _bbox_to_ltrb(box: BBox) -> tuple[int, int, int, int]:
    return box.x, box.y, box.x + box.width, box.y + box.height


def _region_not_found(region_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ApiError(error="region_not_found", message=f"region not found: {region_id}").model_dump(),
    )


def _invalid_region_role(exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=ApiError(error="invalid_region_role", message=str(exc)).model_dump(),
    )


def _build_region_block(
    *,
    box: tuple[int, int, int, int],
    is_content_normalized: bool,
    child_type: BlockChildType,
    role: RegionRole,
    region_id: str,
    source_proposal_id: str,
) -> Block:
    """Construct a new confirmed region ``Block``.

    Shared by ``create_region`` (a person drew this region unprompted —
    ``source_proposal_id`` is the hand-drawn sentinel) and Task 4's
    ``accept_region_proposal`` (a person confirmed a machine's proposal —
    ``source_proposal_id`` is the real proposal id). Both stamp ``region_id``
    and ``source_proposal_id`` into ``additional_block_attributes`` and let
    ``Block.__init__`` raise ``ValueError`` for an unsupported role; the
    caller maps that to the 400 ``invalid_region_role`` envelope.
    """
    left, top, right, bottom = box
    return Block(
        items=[],
        bounding_box=BoundingBox.from_ltrb(left, top, right, bottom, is_normalized=is_content_normalized),
        child_type=child_type,
        block_category=BlockCategory.BLOCK,
        block_role_labels=[role.value],
        additional_block_attributes={
            _REGION_ID_KEY: region_id,
            _SOURCE_PROPOSAL_ID_KEY: source_proposal_id,
        },
    )


def _normalized_role_labels(role: RegionRole) -> list[str]:
    """Validate and normalize ``role`` the same way ``Block.__init__`` does.

    ``Block.block_role_labels`` is a plain attribute, not a validating property, so
    assigning to it directly — as ``edit_region`` must, to avoid re-deriving the
    region's box or membership from a full reconstruction — bypasses
    ``Block._normalize_label`` entirely. That matters beyond a wrong error code:
    ``Block.from_dict`` builds through the validating constructor, so an unsupported
    label written onto a block makes the whole page fail to load on the next read.
    A throwaway, memberless ``Block`` runs the real normalization, aliases and
    whitespace/underscore/hyphen handling included, and raises ``ValueError`` exactly
    as ``create_region``'s constructor does. There is no public single-label validator
    on ``Block``, and hand-checking ``ALLOWED_BLOCK_ROLE_LABELS`` would drift from
    ``_normalize_label``'s alias handling.
    """
    probe = Block(
        items=[],
        child_type=BlockChildType.WORDS,
        block_category=BlockCategory.BLOCK,
        block_role_labels=[role.value],
    )
    return probe.block_role_labels


def _region_owner(page: Page, region: Block) -> Page | Block:
    """Return whatever holds ``region`` — its parent container block, or the page itself.

    Compares by identity, never equality: two regions can carry equal field values and
    still be different objects on the page.
    """
    stack: list[Block] = list(page.items)
    while stack:
        item = stack.pop()
        if any(child is region for child in item.items):
            return item
        stack.extend(child for child in item.items if isinstance(child, Block))
    return page


def _parent_not_nesting_capable(parent_region_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=ApiError(
            error="parent_not_nesting_capable",
            message=f"region {parent_region_id} holds words, not regions; create it with child_type=blocks first",
        ).model_dump(),
    )


# ── Routes: create / edit / delete ──────────────────────────────────────


@router.post(
    "/{project_id}/pages/{page_index}/regions",
    response_model=PagePayload,
    dependencies=[Depends(bind_page_labeling_lease)],
    operation_id="create_region",
)
def create_region(
    *,
    project_id: str,
    page_index: int,
    body: CreateRegionRequest,
    project_state: ProjectState = Depends(get_project_state),
    settings: Settings = Depends(get_settings),
    app_config: AppConfig = Depends(get_app_config),
    store: LabelerPageStore | None = Depends(get_page_store_optional),
) -> JSONResponse:
    """Create a new confirmed region, hand-drawn by a person — no members yet.

    ``child_type="words"`` (the default) makes a leaf region that can hold words via
    the membership route. ``child_type="blocks"`` makes a nesting-capable container
    that can hold other regions but never words directly. ``parent_region_id`` nests
    the new region under an existing container instead of adding it as a top-level
    ``Page.items`` sibling.
    """
    err = _check_project_and_page(project_id, page_index, project_state)
    if err is not None:
        return err

    pstate = project_state.get_page_state(page_index)
    page = _resolve_page_object(pstate)
    if pstate is None or page is None:
        return _page_not_loaded(page_index)

    left, top, right, bottom = _bbox_to_ltrb(body.box)
    region_id = uuid.uuid4().hex
    child_type = BlockChildType.BLOCKS if body.child_type == "blocks" else BlockChildType.WORDS

    page_lock = project_state.get_page_lock(page_index)
    with page_lock:
        parent = None
        if body.parent_region_id is not None:
            parent = find_region_block(page, body.parent_region_id)
            if parent is None:
                return _region_not_found(body.parent_region_id)
            if parent.child_type is not BlockChildType.BLOCKS:
                return _parent_not_nesting_capable(body.parent_region_id)

        try:
            region = _build_region_block(
                box=(left, top, right, bottom),
                is_content_normalized=page.is_content_normalized,
                child_type=child_type,
                role=body.role,
                region_id=region_id,
                source_proposal_id=_HAND_DRAWN_SENTINEL,
            )
        except ValueError as exc:
            return _invalid_region_role(exc)
        # ``Block.add_item`` recomputes the owner's bounding box from its items. A
        # container region's box is what a person drew on the page, not the union of
        # its children — same rule the membership route follows for a leaf region.
        saved_parent_box = parent.bounding_box if parent is not None else None
        (parent if parent is not None else page).add_item(region)
        if parent is not None:
            parent.bounding_box = saved_parent_box
        pstate.generation += 1
        if not _save_to_store_best_effort(
            pstate=pstate,
            store=store,
            changes=[{"type": "region_created", "region_id": region_id, "role": body.role.value}],
        ):
            return _store_persist_failed_response(page_id=pstate.page_id)

    return _refresh_payload_response(
        project_id=project_id, page_index=page_index, project_state=project_state, settings=settings, app_config=app_config,
    )


@router.patch(
    "/{project_id}/pages/{page_index}/regions/{region_id}",
    response_model=PagePayload,
    dependencies=[Depends(bind_page_labeling_lease)],
    operation_id="edit_region",
)
def edit_region(
    *,
    project_id: str,
    page_index: int,
    region_id: str,
    body: EditRegionRequest,
    project_state: ProjectState = Depends(get_project_state),
    settings: Settings = Depends(get_settings),
    app_config: AppConfig = Depends(get_app_config),
    store: LabelerPageStore | None = Depends(get_page_store_optional),
) -> JSONResponse:
    """Edit a region's role and/or box. Box is set directly — it is never re-derived from members."""
    err = _check_project_and_page(project_id, page_index, project_state)
    if err is not None:
        return err

    pstate = project_state.get_page_state(page_index)
    page = _resolve_page_object(pstate)
    if pstate is None or page is None:
        return _page_not_loaded(page_index)

    page_lock = project_state.get_page_lock(page_index)
    with page_lock:
        region = find_region_block(page, region_id)
        if region is None:
            return _region_not_found(region_id)
        if body.role is not None:
            try:
                region.block_role_labels = _normalized_role_labels(body.role)
            except ValueError as exc:
                return _invalid_region_role(exc)
        if body.box is not None:
            left, top, right, bottom = _bbox_to_ltrb(body.box)
            region.bounding_box = BoundingBox.from_ltrb(left, top, right, bottom, is_normalized=page.is_content_normalized)
        pstate.generation += 1
        if not _save_to_store_best_effort(
            pstate=pstate, store=store, changes=[{"type": "region_edited", "region_id": region_id}],
        ):
            return _store_persist_failed_response(page_id=pstate.page_id)

    return _refresh_payload_response(
        project_id=project_id, page_index=page_index, project_state=project_state, settings=settings, app_config=app_config,
    )


@router.delete(
    "/{project_id}/pages/{page_index}/regions/{region_id}",
    response_model=PagePayload,
    dependencies=[Depends(bind_page_labeling_lease)],
    operation_id="delete_region",
)
def delete_region(
    *,
    project_id: str,
    page_index: int,
    region_id: str,
    project_state: ProjectState = Depends(get_project_state),
    settings: Settings = Depends(get_settings),
    app_config: AppConfig = Depends(get_app_config),
    store: LabelerPageStore | None = Depends(get_page_store_optional),
) -> JSONResponse:
    """Delete a region. Its member words (if any) are recovered, never dropped."""
    err = _check_project_and_page(project_id, page_index, project_state)
    if err is not None:
        return err

    pstate = project_state.get_page_state(page_index)
    page = _resolve_page_object(pstate)
    if pstate is None or page is None:
        return _page_not_loaded(page_index)

    page_lock = project_state.get_page_lock(page_index)
    with page_lock:
        region = find_region_block(page, region_id)
        if region is None:
            return _region_not_found(region_id)
        members = list(region.words)
        # A region created with ``parent_region_id`` lives in its parent's ``items``,
        # not in ``page.items``, so ``page.remove_item`` would not find it.
        owner = _region_owner(page, region)
        saved_owner_box = owner.bounding_box if isinstance(owner, Block) else None
        owner.remove_item(region)
        if isinstance(owner, Block):
            owner.bounding_box = saved_owner_box
        if members:
            recovered = build_recovered_words_block(members)
            if recovered is not None:
                page.add_item(recovered)
        pstate.generation += 1
        if not _save_to_store_best_effort(
            pstate=pstate, store=store, changes=[{"type": "region_deleted", "region_id": region_id}],
        ):
            return _store_persist_failed_response(page_id=pstate.page_id)

    return _refresh_payload_response(
        project_id=project_id, page_index=page_index, project_state=project_state, settings=settings, app_config=app_config,
    )


def install_regions_router(app: FastAPI) -> None:
    """Register the regions router. Called from ``bootstrap.build_app``."""
    app.include_router(router)


__all__ = ["CreateRegionRequest", "EditRegionRequest", "install_regions_router", "router"]
```

- [ ] **Step 4: Wire the router into `bootstrap.py`**

Add the import beside the other `.api.*` imports:

```python
from .api.regions import install_regions_router
```

Add the install call right after `install_words_router(app)`:

```python
    install_words_router(app)
    install_regions_router(app)
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/integration/test_regions_router.py -v`
Expected: PASS, all eleven tests.

- [ ] **Step 6: Regression check**

Run: `make AI=1 test`
Expected: PASS with no regressions in the existing suite.

- [ ] **Step 7: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/api/regions.py src/pdomain_ocr_labeler_spa/bootstrap.py \
  tests/integration/test_regions_router.py
git commit -m "feat(regions): add create/edit/delete region routes"
```

---

### Task 3: Region word-membership route

Membership is an explicit edge, not a consequence of geometry. Setting it replaces the region's
member set exactly: words no longer listed are released back to their line (or, if that leaves them
orphaned, wrapped as `recovered`); words newly listed are moved out of wherever they currently sit.

**Files:**

- Modify: `src/pdomain_ocr_labeler_spa/api/regions.py`
- Test: `tests/integration/test_regions_router.py` (extended)

**Interfaces:**

- Consumes: `find_region_block` (Task 2); `_word_not_found` from `.words`; `Block.words`,
  `Block.items`, `Block.add_item`, `Block.remove_item`, `Page.lines` from `pdomain_book_tools.ocr`.
- Produces: `PUT .../regions/{region_id}/words` (`set_region_word_membership`), returning the full
  `PagePayload`; `_resolve_target_word` and `_region_not_word_capable` in `api/regions.py`.

- [ ] **Step 1: Write the failing test**

Append to `tests/integration/test_regions_router.py`:

```python
def test_set_membership_moves_words_into_the_region(toolbar_loaded: Any) -> None:
    client, _ps, page = toolbar_loaded
    created = client.post(
        f"{_BASE}/regions",
        json={"role": "poetry", "box": {"x": 0, "y": 0, "width": 200, "height": 300}},
    ).json()
    region_id = next(reg["region_id"] for reg in created["regions"] if reg["confirmed"])

    r = client.put(
        f"{_BASE}/regions/{region_id}/words",
        json={"word_refs": [{"line_index": 0, "word_index": 0}, {"line_index": 0, "word_index": 1}]},
    )
    assert r.status_code == 200, r.text
    from pdomain_ocr_labeler_spa.api.regions import find_region_block

    region = find_region_block(page, region_id)
    assert region is not None
    assert {w.text for w in region.words} == {"one", "two"}
    assert len(page.lines[0].words) == 0


def test_set_membership_preserves_the_explicit_box(toolbar_loaded: Any) -> None:
    client, _ps, page = toolbar_loaded
    created = client.post(
        f"{_BASE}/regions",
        json={"role": "poetry", "box": {"x": 1, "y": 1, "width": 199, "height": 299}},
    ).json()
    region_id = next(reg["region_id"] for reg in created["regions"] if reg["confirmed"])

    r = client.put(f"{_BASE}/regions/{region_id}/words", json={"word_refs": [{"line_index": 0, "word_index": 0}]})
    assert r.status_code == 200, r.text
    region = next(reg for reg in r.json()["regions"] if reg["region_id"] == region_id)
    # Box stays what was explicitly set — never re-derived from the union of member words.
    assert region["box"] == {"x": 1, "y": 1, "width": 199, "height": 299}


def test_set_membership_replaces_the_prior_set(toolbar_loaded: Any) -> None:
    client, _ps, page = toolbar_loaded
    created = client.post(
        f"{_BASE}/regions",
        json={"role": "poetry", "box": {"x": 0, "y": 0, "width": 200, "height": 300}},
    ).json()
    region_id = next(reg["region_id"] for reg in created["regions"] if reg["confirmed"])
    client.put(f"{_BASE}/regions/{region_id}/words", json={"word_refs": [{"line_index": 0, "word_index": 0}]})

    # word_index 0, not 1: the first PUT moved "one" out of line 0, so "two" has
    # shifted down to index 0. Positions resolve against the live tree on every
    # request — that is the design, and a stale index here 404s.
    r = client.put(f"{_BASE}/regions/{region_id}/words", json={"word_refs": [{"line_index": 0, "word_index": 0}]})
    assert r.status_code == 200, r.text
    from pdomain_ocr_labeler_spa.api.regions import find_region_block

    region = find_region_block(page, region_id)
    assert region is not None
    assert {w.text for w in region.words} == {"two"}
    # The released word ("one") comes back as a recovered block, not dropped.
    assert any("recovered" in b.block_role_labels for b in page.items)


def test_set_membership_on_unknown_region_returns_404(toolbar_loaded: Any) -> None:
    client, _ps, _page = toolbar_loaded
    r = client.put(f"{_BASE}/regions/does-not-exist/words", json={"word_refs": []})
    assert r.status_code == 404, r.text


def test_set_membership_on_unknown_word_returns_404(toolbar_loaded: Any) -> None:
    client, _ps, _page = toolbar_loaded
    created = client.post(
        f"{_BASE}/regions",
        json={"role": "poetry", "box": {"x": 0, "y": 0, "width": 200, "height": 300}},
    ).json()
    region_id = next(reg["region_id"] for reg in created["regions"] if reg["confirmed"])
    r = client.put(f"{_BASE}/regions/{region_id}/words", json={"word_refs": [{"line_index": 99, "word_index": 0}]})
    assert r.status_code == 404, r.text
    assert r.json()["error"] == "word_not_found"


def test_set_membership_on_a_container_region_returns_400(toolbar_loaded: Any) -> None:
    """A container region (``child_type=blocks``) holds regions, not words — the
    mirror image of ``parent_not_nesting_capable``. The rejection must land before
    any word is moved out of its line.
    """
    client, _ps, page = toolbar_loaded
    container = client.post(
        f"{_BASE}/regions",
        json={
            "role": "figure",
            "box": {"x": 0, "y": 0, "width": 200, "height": 300},
            "child_type": "blocks",
        },
    ).json()
    container_id = next(reg["region_id"] for reg in container["regions"] if reg["confirmed"])

    r = client.put(
        f"{_BASE}/regions/{container_id}/words", json={"word_refs": [{"line_index": 0, "word_index": 0}]}
    )
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "region_not_word_capable"
    # Nothing moved before the rejection — the word is still on its original line.
    assert {w.text for w in page.lines[0].words} == {"one", "two"}


# Moved here from Task 2: it needs the membership route above to put words in the
# region before deleting it. Under Task 2 alone the PUT 404s, the region has no
# members, and the recovered-block assertion cannot pass.
def test_delete_region_recovers_its_member_words(toolbar_loaded: Any) -> None:
    client, _ps, page = toolbar_loaded
    created = client.post(
        f"{_BASE}/regions",
        json={"role": "poetry", "box": {"x": 0, "y": 0, "width": 200, "height": 300}},
    ).json()
    region_id = next(reg["region_id"] for reg in created["regions"] if reg["confirmed"])
    client.put(f"{_BASE}/regions/{region_id}/words", json={"word_refs": [{"line_index": 0, "word_index": 0}]})

    before_word_count = len(page.words)
    r = client.delete(f"{_BASE}/regions/{region_id}")
    assert r.status_code == 200, r.text
    assert len(page.words) == before_word_count
    assert any("recovered" in b.block_role_labels for b in page.items)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_regions_router.py -v -k membership`
Expected: FAIL — `404 Not Found` (no route registered yet).

- [ ] **Step 3: Add the membership route**

In `src/pdomain_ocr_labeler_spa/api/regions.py`, add near the top of the request-model section:

```python
class WordRef(BaseModel):
    line_index: int
    word_index: int


class SetRegionWordMembershipRequest(BaseModel):
    word_refs: list[WordRef]
```

Add a resolver helper beside `_bbox_to_ltrb`:

`_word_not_found` already exists in `api/words.py` — import it rather than defining a second copy.

```python
def _resolve_target_word(page: Page, line_index: int, word_index: int) -> Word | None:
    """Resolve the word at ``(line_index, word_index)`` in the *current* live tree.

    Positional and resolved once, at request time, exactly like ``_resolve_word``
    in ``api/words.py`` — never persisted as a stored key. Line numbering is
    renumbered by the band-identification fixes, so nothing here stores this pair.
    """
    lines = page.lines
    if not (0 <= line_index < len(lines)):
        return None
    words = lines[line_index].words
    if not (0 <= word_index < len(words)):
        return None
    return words[word_index]


def _region_not_word_capable(region_id: str) -> JSONResponse:
    """A container region holds regions, not words — the mirror of ``parent_not_nesting_capable``.

    Without this, ``Block.add_item`` raises ``TypeError`` when a ``Word`` is added to a
    ``child_type=BLOCKS`` block and the route answers a reachable request with a 500.
    """
    return JSONResponse(
        status_code=400,
        content=ApiError(
            error="region_not_word_capable",
            message=f"region {region_id} holds regions, not words; address a leaf region instead",
        ).model_dump(),
    )
```

Add the route after `delete_region`:

```python
@router.put(
    "/{project_id}/pages/{page_index}/regions/{region_id}/words",
    response_model=PagePayload,
    dependencies=[Depends(bind_page_labeling_lease)],
    operation_id="set_region_word_membership",
)
def set_region_word_membership(
    *,
    project_id: str,
    page_index: int,
    region_id: str,
    body: SetRegionWordMembershipRequest,
    project_state: ProjectState = Depends(get_project_state),
    settings: Settings = Depends(get_settings),
    app_config: AppConfig = Depends(get_app_config),
    store: LabelerPageStore | None = Depends(get_page_store_optional),
) -> JSONResponse:
    """Replace a region's word membership exactly with the given set.

    Only a leaf (``child_type=WORDS``) region can hold words directly; a container
    region rejects this route with 400 ``region_not_word_capable``, checked right
    after the region resolves and before any word is resolved or moved, mirroring
    ``create_region``'s ``parent_not_nesting_capable`` check for the opposite shape.

    A word not listed is released; a word newly listed is moved out of wherever it
    currently sits. ``Block.add_item``/``remove_item`` recompute the block's bounding
    box from its items as a side effect — the region's own explicitly-set box is saved
    before the edit and restored after, because a region's box is not its membership.
    """
    err = _check_project_and_page(project_id, page_index, project_state)
    if err is not None:
        return err

    pstate = project_state.get_page_state(page_index)
    page = _resolve_page_object(pstate)
    if pstate is None or page is None:
        return _page_not_loaded(page_index)

    page_lock = project_state.get_page_lock(page_index)
    with page_lock:
        region = find_region_block(page, region_id)
        if region is None:
            return _region_not_found(region_id)
        if region.child_type is not BlockChildType.WORDS:
            return _region_not_word_capable(region_id)

        target_words: list[Word] = []
        for ref in body.word_refs:
            word = _resolve_target_word(page, ref.line_index, ref.word_index)
            if word is None:
                return _word_not_found(ref.line_index, ref.word_index)
            target_words.append(word)

        saved_box = region.bounding_box

        # Identity, not equality: ``Word`` may compare equal by value, and two words
        # with the same text and box are still different objects on the page.
        released = [w for w in region.words if not any(w is t for t in target_words)]
        for word in released:
            region.remove_item(word)
        if released:
            recovered = build_recovered_words_block(released)
            if recovered is not None:
                page.add_item(recovered)

        for word in target_words:
            if any(w is word for w in region.words):
                continue
            owner_line = next((ln for ln in page.lines if any(w is word for w in ln.words)), None)
            if owner_line is not None:
                owner_line.remove_item(word)
            region.add_item(word)

        region.bounding_box = saved_box

        pstate.generation += 1
        if not _save_to_store_best_effort(
            pstate=pstate,
            store=store,
            changes=[{"type": "region_membership_set", "region_id": region_id, "word_count": len(target_words)}],
        ):
            return _store_persist_failed_response(page_id=pstate.page_id)

    return _refresh_payload_response(
        project_id=project_id, page_index=page_index, project_state=project_state, settings=settings, app_config=app_config,
    )
```

Add `SetRegionWordMembershipRequest` and `WordRef` to `__all__`.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/integration/test_regions_router.py -v`
Expected: PASS, all eighteen tests (eleven from Task 2, seven new).

- [ ] **Step 5: Regenerate the OpenAPI contract**

Run: `make openapi-export`
Expected: `frontend/src/api/types.ts` changes to include the four new routes so far.

- [ ] **Step 6: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/api/regions.py tests/integration/test_regions_router.py \
  frontend/src/api/types.ts
git commit -m "feat(regions): add explicit word-membership route"
```

---

### Task 4: Proposal routes — list, accept, reject

Accept and reject close the gap the glyph accept-prediction pattern left open: accept persists the
proposal into a new confirmed `Block` and records the decision; reject records `verified_negative`
with no page mutation, so "nobody has looked" and "looked and refused" are never confused.

**Files:**

- Modify: `src/pdomain_ocr_labeler_spa/api/regions.py`
- Test: `tests/integration/test_region_proposals_router.py`

**Interfaces:**

- Consumes: `RegionProposal`, `RegionDecision`, `Disposition` from `..core.regions.models`;
  `RegionProposalLog`, `RegionDecisionLog` from `..core.regions.proposal_log` /
  `.decision_log`; `_build_region_block` and `find_region_block` (Task 2).
- Produces: `GET .../regions/proposals` (`list_region_proposals`, returns
  `ListRegionProposalsResponse`), `POST .../regions/proposals/{proposal_id}/accept`
  (`accept_region_proposal`), `POST .../regions/proposals/{proposal_id}/reject`
  (`reject_region_proposal`), the latter two returning the full `PagePayload`.

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_region_proposals_router.py
"""Integration tests for the region proposal list/accept/reject routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

_BASE = "/api/projects/book1/pages/0"


def _seed_proposal(client: Any, project_root: Path, *, proposal_id: str = "p1", confidence: float = 0.8) -> None:
    from pdomain_book_contracts.annotation import RegionRole

    from pdomain_ocr_labeler_spa.core.regions.models import ProposalRun, RegionProposal
    from pdomain_ocr_labeler_spa.core.regions.proposal_log import RegionProposalLog

    log = RegionProposalLog(project_root)
    log.append_run(
        ProposalRun(
            run_id="r1",
            model_id="test-detector",
            model_version="0.0.0",
            created_at="2026-09-08T10:00:00+00:00",
            page_facet_digests={0: {"word_boxes": "a" * 64}},
            depends_on=frozenset({"word_boxes"}),
            page_kind_decision_ref=None,
            page_kind_was_confirmed=False,
        )
    )
    log.append_proposals(
        [
            RegionProposal(
                proposal_id=proposal_id,
                run_id="r1",
                page_index=0,
                role=RegionRole.POETRY,
                box=(5, 5, 50, 50),
                confidence=confidence,
                evidence={"signal": "indent"},
            )
        ]
    )


def test_list_proposals_returns_confidence_and_evidence(toolbar_loaded: Any) -> None:
    client, project_state, _page = toolbar_loaded
    _seed_proposal(client, project_state.loaded_project.project_root)

    r = client.get(f"{_BASE}/regions/proposals")
    assert r.status_code == 200, r.text
    proposals = r.json()["proposals"]
    assert len(proposals) == 1
    assert proposals[0]["confidence"] == 0.8
    assert proposals[0]["evidence"] == {"signal": "indent"}
    assert proposals[0]["disposition"] is None


def test_accept_proposal_creates_a_confirmed_region(toolbar_loaded: Any) -> None:
    client, project_state, page = toolbar_loaded
    _seed_proposal(client, project_state.loaded_project.project_root)

    r = client.post(f"{_BASE}/regions/proposals/p1/accept")
    assert r.status_code == 200, r.text
    body = r.json()
    confirmed = [reg for reg in body["regions"] if reg["confirmed"]]
    assert len(confirmed) == 1
    assert confirmed[0]["role"] == "poetry"
    assert confirmed[0]["box"] == {"x": 5, "y": 5, "width": 45, "height": 45}
    assert confirmed[0]["proposal_id"] == "p1"
    assert any(b.additional_block_attributes.get("region_id") == confirmed[0]["region_id"] for b in page.items)


def test_accept_leaves_the_proposal_record_byte_identical(toolbar_loaded: Any) -> None:
    client, project_state, _page = toolbar_loaded
    project_root = project_state.loaded_project.project_root
    _seed_proposal(client, project_root)
    before = (project_root / ".pd-pages" / "region-proposals.jsonl").read_bytes()

    client.post(f"{_BASE}/regions/proposals/p1/accept")

    after = (project_root / ".pd-pages" / "region-proposals.jsonl").read_bytes()
    assert after.startswith(before)


def test_reject_proposal_records_a_verified_negative_decision(toolbar_loaded: Any) -> None:
    client, project_state, page = toolbar_loaded
    project_root = project_state.loaded_project.project_root
    _seed_proposal(client, project_root)
    before_items = len(page.items)

    r = client.post(f"{_BASE}/regions/proposals/p1/reject")
    assert r.status_code == 200, r.text
    # No page mutation on reject — the page blob is only ever written by a human
    # *confirming* something, and a rejection confirms nothing new about the page.
    assert len(page.items) == before_items

    from pdomain_ocr_labeler_spa.core.regions.decision_log import RegionDecisionLog
    from pdomain_ocr_labeler_spa.core.regions.models import Disposition

    decision = RegionDecisionLog(project_root).decision_for("p1", run_id="r1")
    assert decision is not None
    assert decision.disposition is Disposition.REJECTED


def test_a_rejected_proposal_never_reappears_in_the_resolved_list(toolbar_loaded: Any) -> None:
    client, project_state, _page = toolbar_loaded
    _seed_proposal(client, project_state.loaded_project.project_root)
    client.post(f"{_BASE}/regions/proposals/p1/reject")

    r = client.get(_BASE)
    assert r.status_code == 200, r.text
    assert all(reg.get("proposal_id") != "p1" for reg in r.json()["regions"])


def test_accept_unknown_proposal_returns_404(toolbar_loaded: Any) -> None:
    client, _ps, _page = toolbar_loaded
    r = client.post(f"{_BASE}/regions/proposals/does-not-exist/accept")
    assert r.status_code == 404, r.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_region_proposals_router.py -v`
Expected: FAIL — `404 Not Found` on every proposal route.

- [ ] **Step 3: Add the proposal routes**

In `src/pdomain_ocr_labeler_spa/api/regions.py`, add to the imports:

```python
from datetime import UTC, datetime

from ..core.regions.decision_log import RegionDecisionLog
from ..core.regions.models import Disposition, RegionDecision, RegionProposal
from ..core.regions.proposal_log import RegionProposalLog
```

Add request/response models beside `SetRegionWordMembershipRequest`:

```python
class AcceptRegionProposalRequest(BaseModel):
    """Optional overrides. Present -> disposition is ``edited``; absent -> ``accepted``."""

    role: RegionRole | None = None
    box: BBox | None = None


class RejectRegionProposalRequest(BaseModel):
    pass


class RegionProposalListItem(BaseModel):
    proposal_id: str
    run_id: str
    role: RegionRole
    box: BBox
    confidence: float
    evidence: dict[str, Any]
    disposition: str | None = None


class ListRegionProposalsResponse(BaseModel):
    proposals: list[RegionProposalListItem]
```

Add a lookup helper beside `_resolve_line_and_word`:

```python
def _find_proposal(store: RegionProposalLog, page_index: int, proposal_id: str) -> RegionProposal | None:
    for proposal in store.proposals_for_page(page_index):
        if proposal.proposal_id == proposal_id:
            return proposal
    return None


def _proposal_not_found(proposal_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ApiError(error="proposal_not_found", message=f"proposal not found: {proposal_id}").model_dump(),
    )


def _decision_persist_failed_response(*, proposal_id: str) -> JSONResponse:
    """503 when a region decision could not be durably persisted (mirrors
    ``_store_persist_failed_response`` in ``api/words.py``, for the decision log
    rather than the page store).
    """
    return JSONResponse(
        status_code=503,
        content=ApiError(
            error="decision_persist_failed",
            message=f"decision could not be persisted to the decision log (proposal_id={proposal_id})",
        ).model_dump(),
    )


def _append_decision_or_error(
    decision_log: RegionDecisionLog, decision: RegionDecision
) -> JSONResponse | None:
    """Append ``decision``; return ``None`` on success or a 503 envelope on I/O failure.

    A disk-full, permission, or concurrent-write failure on the decision log is a
    reachable I/O failure, same as the page-store writes ``_save_to_store_best_effort``
    guards — no route in this codebase lets a reachable request fall through to the
    catch-all handler's 500.
    """
    try:
        decision_log.append(decision)
    except OSError as exc:
        log.warning(
            "decision log append failed proposal_id=%s run_id=%s: %s",
            decision.proposal_id,
            decision.run_id,
            exc,
        )
        return _decision_persist_failed_response(proposal_id=decision.proposal_id)
    return None
```

Add the three routes after `set_region_word_membership`:

```python
@router.get(
    "/{project_id}/pages/{page_index}/regions/proposals",
    response_model=ListRegionProposalsResponse,
    operation_id="list_region_proposals",
)
def list_region_proposals(
    project_id: str,
    page_index: int,
    project_state: ProjectState = Depends(get_project_state),
) -> JSONResponse:
    """List every proposal for this page, across every run, with confidence and evidence."""
    err = _check_project_and_page(project_id, page_index, project_state)
    if err is not None:
        return err
    project = project_state.loaded_project
    assert project is not None  # narrowed by _check_project_and_page

    proposal_log = RegionProposalLog(project.project_root)
    decision_log = RegionDecisionLog(project.project_root)
    items = []
    for p in proposal_log.proposals_for_page(page_index):
        decision = decision_log.decision_for(p.proposal_id, run_id=p.run_id)
        items.append(
            RegionProposalListItem(
                proposal_id=p.proposal_id,
                run_id=p.run_id,
                role=p.role,
                box=BBox(x=p.box[0], y=p.box[1], width=p.box[2] - p.box[0], height=p.box[3] - p.box[1]),
                confidence=p.confidence,
                evidence=p.evidence,
                disposition=decision.disposition.value if decision is not None else None,
            )
        )
    response = ListRegionProposalsResponse(proposals=items)
    return JSONResponse(status_code=200, content=response.model_dump(mode="json"))


@router.post(
    "/{project_id}/pages/{page_index}/regions/proposals/{proposal_id}/accept",
    response_model=PagePayload,
    dependencies=[Depends(bind_page_labeling_lease)],
    operation_id="accept_region_proposal",
)
def accept_region_proposal(
    *,
    project_id: str,
    page_index: int,
    proposal_id: str,
    body: AcceptRegionProposalRequest = AcceptRegionProposalRequest(),
    project_state: ProjectState = Depends(get_project_state),
    settings: Settings = Depends(get_settings),
    app_config: AppConfig = Depends(get_app_config),
    store: LabelerPageStore | None = Depends(get_page_store_optional),
) -> JSONResponse:
    """Accept a proposal: create the confirmed region it describes and record the decision.

    The proposal record itself is never touched — only a new confirmed ``Block`` and a
    new ``RegionDecision`` are written. An override in the request body records
    ``edited`` instead of ``accepted``, per ``Disposition.knowledge_state`` (both map to
    ``KnowledgeState.POSITIVE``; only ``rejected`` is a refusal).
    """
    err = _check_project_and_page(project_id, page_index, project_state)
    if err is not None:
        return err
    project = project_state.loaded_project
    assert project is not None

    pstate = project_state.get_page_state(page_index)
    page = _resolve_page_object(pstate)
    if pstate is None or page is None:
        return _page_not_loaded(page_index)

    proposal_log = RegionProposalLog(project.project_root)
    proposal = _find_proposal(proposal_log, page_index, proposal_id)
    if proposal is None:
        return _proposal_not_found(proposal_id)

    role = body.role if body.role is not None else proposal.role
    box = _bbox_to_ltrb(body.box) if body.box is not None else proposal.box
    has_override = body.role is not None or body.box is not None
    disposition = Disposition.EDITED if has_override else Disposition.ACCEPTED
    decision_log = RegionDecisionLog(project.project_root)

    page_lock = project_state.get_page_lock(page_index)
    with page_lock:
        # Accepting twice must not create a second region for one proposal — a double
        # click is enough. If a decision already exists and the region it names still
        # resolves, the accept already happened; return the current payload unchanged.
        # If the region was deleted since, fall through: deleting it and accepting
        # again is a legitimate new decision, not a duplicate.
        existing_decision = decision_log.decision_for(proposal_id, run_id=proposal.run_id)
        existing_region_id = existing_decision.region_id if existing_decision is not None else None
        if existing_region_id is not None and find_region_block(page, existing_region_id) is not None:
            return _refresh_payload_response(
                project_id=project_id,
                page_index=page_index,
                project_state=project_state,
                settings=settings,
                app_config=app_config,
            )

        region_id = uuid.uuid4().hex
        try:
            region = _build_region_block(
                box=box,
                is_content_normalized=page.is_content_normalized,
                child_type=BlockChildType.WORDS,
                role=role,
                region_id=region_id,
                source_proposal_id=proposal_id,
            )
        except ValueError as exc:
            return _invalid_region_role(exc)
        page.add_item(region)
        pstate.generation += 1
        if not _save_to_store_best_effort(
            pstate=pstate,
            store=store,
            changes=[{"type": "region_proposal_accepted", "proposal_id": proposal_id, "region_id": region_id}],
        ):
            return _store_persist_failed_response(page_id=pstate.page_id)

        # Page blob first, decision second, both under the lock. Neither order is
        # transactional, so choose by which failure is worse: a confirmed region with
        # no decision reads as "nobody has looked yet" — the confusion this design
        # exists to prevent — but is recoverable, because the block carries
        # ``source_proposal_id``. A decision naming a region that was never written
        # is not recoverable.
        decision_err = _append_decision_or_error(
            decision_log,
            RegionDecision(
                decision_id=uuid.uuid4().hex,
                run_id=proposal.run_id,
                proposal_id=proposal_id,
                disposition=disposition,
                region_id=region_id,
                actor="default",
                decided_at=datetime.now(UTC).isoformat(),
            ),
        )
        if decision_err is not None:
            return decision_err

    return _refresh_payload_response(
        project_id=project_id, page_index=page_index, project_state=project_state, settings=settings, app_config=app_config,
    )


@router.post(
    "/{project_id}/pages/{page_index}/regions/proposals/{proposal_id}/reject",
    response_model=PagePayload,
    operation_id="reject_region_proposal",
)
def reject_region_proposal(
    *,
    project_id: str,
    page_index: int,
    proposal_id: str,
    _body: RejectRegionProposalRequest = RejectRegionProposalRequest(),
    project_state: ProjectState = Depends(get_project_state),
    settings: Settings = Depends(get_settings),
    app_config: AppConfig = Depends(get_app_config),
) -> JSONResponse:
    """Reject a proposal. Records ``verified_negative``; never touches the page blob."""
    err = _check_project_and_page(project_id, page_index, project_state)
    if err is not None:
        return err
    project = project_state.loaded_project
    assert project is not None

    proposal_log = RegionProposalLog(project.project_root)
    proposal = _find_proposal(proposal_log, page_index, proposal_id)
    if proposal is None:
        return _proposal_not_found(proposal_id)

    decision_log = RegionDecisionLog(project.project_root)
    decision_err = _append_decision_or_error(
        decision_log,
        RegionDecision(
            decision_id=uuid.uuid4().hex,
            run_id=proposal.run_id,
            proposal_id=proposal_id,
            disposition=Disposition.REJECTED,
            region_id=None,
            actor="default",
            decided_at=datetime.now(UTC).isoformat(),
        ),
    )
    if decision_err is not None:
        return decision_err

    return _refresh_payload_response(
        project_id=project_id, page_index=page_index, project_state=project_state, settings=settings, app_config=app_config,
    )
```

Add the new request/response classes to `__all__`.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/integration/test_region_proposals_router.py -v`
Expected: PASS, all eleven tests — the six below plus five more you must add: an accept whose
proposal carries a role `Block.ALLOWED_BLOCK_ROLE_LABELS` does not allow returns 400 and adds no
region; a second accept of the same proposal adds no second region; an accept after its region was
deleted creates a fresh one; and a failing decision-log append returns the 503 envelope rather than
a 500, on both accept and reject.

- [ ] **Step 5: Regenerate the OpenAPI contract and run the full suite**

```bash
make openapi-export
make AI=1 test
```

Expected: `types.ts` picks up the three new routes; full suite passes.

- [ ] **Step 6: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/api/regions.py tests/integration/test_region_proposals_router.py \
  frontend/src/api/types.ts
git commit -m "feat(regions): add list/accept/reject proposal routes"
```

---

### Task 5: The proposal-run job and the book-scoped route

The job never computes real proposals in this plan — that is slice 4's geometry engine, gated on
work this plan does not do. What it builds is the scaffolding slice 4 plugs into: a job type, a
per-run facet-digest snapshot, a swappable `RegionDetector` callable defaulting to one that proposes
nothing, and a guard that reads each page's page-kind state itself rather than trusting a caller's
say-so — a page whose kind was never proposed or confirmed gets no region proposals.

**Files:**

- Create: `src/pdomain_ocr_labeler_spa/core/regions/detector.py`
- Create: `src/pdomain_ocr_labeler_spa/core/jobs/handlers/propose_regions.py`
- Modify: `src/pdomain_ocr_labeler_spa/core/jobs/runner.py`
- Modify: `src/pdomain_ocr_labeler_spa/api/regions.py`
- Test: `tests/unit/core/regions/test_detector.py`
- Test: `tests/integration/test_region_proposals_router.py` (extended)

**Interfaces:**

- Consumes: `ProposalRun`, `RegionProposal` from `..regions.models`; `RegionProposalLog` from
  `..regions.proposal_log`; `compute_page_facet_digests` from `..regions.block_adapter` (Task 1);
  `PageKindProposalLog` from `..page_kind.proposal_log` and `PageKindReviewedStore` from
  `..page_kind.reviewed_store` (both from the page-kind-end-to-end plan — see Global Constraints);
  `JobRunner`, `Job` from `core/jobs/runner.py`; `runner.context` (`project_state`, `page_store`) —
  same context keys `save_project` already reads.
- Produces: `DetectedRegion`, `RegionDetector`, `null_region_detector` in
  `core/regions/detector.py`; `handle_propose_regions(runner, job)` in
  `core/jobs/handlers/propose_regions.py`; job type `"propose_regions"` registered in
  `_HANDLERS`; `POST /{project_id}/regions/propose` (`start_region_proposal_run`), returning
  `202 {job_id}`.

- [ ] **Step 1: Write the failing detector test**

```python
# tests/unit/core/regions/test_detector.py
"""Unit tests for the pluggable region detector interface."""

from __future__ import annotations


def test_the_null_detector_proposes_nothing() -> None:
    from pdomain_book_tools.ocr.page import Page

    from pdomain_ocr_labeler_spa.core.regions.detector import null_region_detector

    page = Page(width=200, height=300, page_index=0, blocks=[])
    assert null_region_detector(page) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/regions/test_detector.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named '...core.regions.detector'`

- [ ] **Step 3: Write the detector interface**

Create `src/pdomain_ocr_labeler_spa/core/regions/detector.py`:

```python
"""The pluggable region-detector seam a proposal run calls.

Mirrors ``pdomain_book_tools.layout.registry``'s ``NullDetector`` naming: a
default that proposes nothing, so the job scaffolding is runnable and testable
before slice 4's real geometry engine exists. Slice 4 supplies a real
``RegionDetector`` through ``JobRunner.context["region_detector"]`` — this
plan does not compute a single proposal itself.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from pdomain_book_contracts.annotation import RegionRole


@dataclass(frozen=True)
class DetectedRegion:
    """One region a detector proposed for one page, before it is wrapped as a ``RegionProposal``."""

    role: RegionRole
    box: tuple[int, int, int, int]
    confidence: float
    evidence: dict[str, Any]


RegionDetector = Callable[[Any], Sequence[DetectedRegion]]
"""Takes a ``pdomain_book_tools.ocr.page.Page`` and returns what it detected."""


def null_region_detector(page: Any) -> list[DetectedRegion]:
    """The default detector: proposes nothing. Keeps the job runnable before slice 4 lands."""
    del page  # unused — this is the explicit no-op the seam defaults to
    return []


__all__ = ["DetectedRegion", "RegionDetector", "null_region_detector"]
```

- [ ] **Step 4: Run the detector test**

Run: `uv run pytest tests/unit/core/regions/test_detector.py -v`
Expected: PASS.

- [ ] **Step 5: Write the job handler**

Create `src/pdomain_ocr_labeler_spa/core/jobs/handlers/propose_regions.py`:

```python
"""``propose_regions`` job handler — book-scoped region proposal run.

Iterates every currently-loaded page whose page kind has been proposed or
confirmed — reading that state itself from the page-kind stores, never
trusting a caller's say-so — snapshots each such page's facet digests so the
run can be traced to the exact facets it read, calls the injected (or default
no-op) detector, and appends whatever it returns to the proposal journal.
Never calls ``save_page_content_to_store`` or ``save_page_to_store`` — a
proposal run is a machine's claim, and the page blob is only ever written by
a human action.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from ...page_kind.proposal_log import PageKindProposalLog
from ...page_kind.reviewed_store import PageKindReviewedStore
from ...project_state import ProjectState
from ...regions.block_adapter import compute_page_facet_digests
from ...regions.detector import RegionDetector, null_region_detector
from ...regions.models import ProposalRun, RegionProposal
from ...regions.proposal_log import RegionProposalLog

if TYPE_CHECKING:
    from ..runner import Job, JobRunner

log = logging.getLogger(__name__)

#: A geometry detector reads word boxes, line/paragraph structure, and the
#: page image — never OCR/ground-truth text — so a text-only edit never
#: invalidates its proposals (spec §"A proposal goes stale per facet, not per
#: page"). Slice 4's real detector may narrow this; this scaffolding detector
#: proposes nothing, so a conservative default is safe here.
_GEOMETRY_FACETS = frozenset({"word_boxes", "line_structure", "page_image"})


def _get_required_context(runner: "JobRunner") -> tuple[ProjectState, Any]:
    """Pull ``project_state`` and the optional ``page_store`` off ``runner.context``."""
    ctx: dict[str, Any] = runner.context
    project_state = ctx.get("project_state")
    if not isinstance(project_state, ProjectState):
        raise RuntimeError("propose_regions: runner.context['project_state'] is not wired")
    return project_state, ctx.get("page_store")


def _image_digest(page_store: Any, page_id: str | None) -> str | None:
    """Best-effort image-facet digest, read off the page's provenance chain."""
    if page_store is None or page_id is None:
        return None
    try:
        agg = page_store.get_page(page_id)
    except Exception:  # pragma: no cover - defensive; a missing aggregate just skips the digest
        return None
    head = agg.record.provenance.head if agg.record.provenance else None
    if head is None or not head.blob_refs:
        return None
    return head.blob_refs[1] if len(head.blob_refs) > 1 else head.blob_refs[0]


async def handle_propose_regions(runner: "JobRunner", job: "Job") -> None:
    project_state, page_store = _get_required_context(runner)
    project = project_state.loaded_project
    if project is None:
        await runner.update_progress(job.job_id, current=0, total=0, message="No project loaded")
        return

    page_indices = sorted(
        idx for idx, pstate in project_state.page_states.items() if pstate.page_record is not None
    )
    if not page_indices:
        await runner.update_progress(job.job_id, current=0, total=0, message="No pages loaded")
        return

    # The job reads page-kind state itself rather than trusting a caller's
    # say-so — a request field the handler never checked would let a caller
    # propose regions for a book whose page kinds were never proposed or
    # confirmed, silently breaking the ordering the design depends on.
    page_kind_proposals = PageKindProposalLog(project.project_root)
    page_kind_reviewed = PageKindReviewedStore(project.project_root)

    def _page_kind_confirmed(idx: int) -> bool:
        page = project_state.page_states[idx].page_record.payload
        return getattr(page, "page_kind", None) is not None or page_kind_reviewed.is_reviewed(idx)

    eligible_indices: list[int] = []
    skipped_indices: list[int] = []
    for idx in page_indices:
        has_kind_state = _page_kind_confirmed(idx) or page_kind_proposals.latest_proposal_for_page(idx) is not None
        (eligible_indices if has_kind_state else skipped_indices).append(idx)

    total = len(eligible_indices)
    if total == 0:
        await runner.update_progress(
            job.job_id,
            current=0,
            total=0,
            message="No page has a proposed or confirmed page kind; nothing to propose regions for",
        )
        return

    detector: RegionDetector = runner.context.get("region_detector", null_region_detector)

    page_facet_digests: dict[int, dict[str, str]] = {}
    for idx in eligible_indices:
        pstate = project_state.page_states[idx]
        page = pstate.page_record.payload if pstate.page_record is not None else None
        if page is None:
            continue
        image_digest = _image_digest(page_store, pstate.page_id)
        page_facet_digests[idx] = compute_page_facet_digests(page, image_digest=image_digest)

    kind_runs = page_kind_proposals.runs()
    run_id = uuid.uuid4().hex
    run = ProposalRun(
        run_id=run_id,
        model_id=str(job.payload.get("model_id", "null-detector")),
        model_version=str(job.payload.get("model_version", "0.0.0")),
        created_at=datetime.now(UTC).isoformat(),
        page_facet_digests=page_facet_digests,
        depends_on=_GEOMETRY_FACETS,
        page_kind_decision_ref=kind_runs[-1].run_id if kind_runs else None,
        page_kind_was_confirmed=all(_page_kind_confirmed(idx) for idx in eligible_indices),
    )

    proposal_log = RegionProposalLog(project.project_root)
    proposal_log.append_run(run)

    if skipped_indices:
        log.info(
            "propose_regions: run=%s project=%s skipped %d page(s) with no page-kind state: %s",
            run_id, project.project_id, len(skipped_indices), skipped_indices,
        )

    await runner.update_progress(
        job.job_id, current=0, total=total, message=f"Proposing regions for {total} page(s)"
    )
    proposal_count = 0
    for i, idx in enumerate(eligible_indices, start=1):
        pstate = project_state.page_states[idx]
        page = pstate.page_record.payload if pstate.page_record is not None else None
        if page is not None and hasattr(page, "lines"):
            detected = detector(page)
            if detected:
                proposals = [
                    RegionProposal(
                        proposal_id=uuid.uuid4().hex,
                        run_id=run_id,
                        page_index=idx,
                        role=d.role,
                        box=d.box,
                        confidence=d.confidence,
                        evidence=d.evidence,
                    )
                    for d in detected
                ]
                proposal_log.append_proposals(proposals)
                proposal_count += len(proposals)
        await runner.update_progress(job.job_id, current=i, total=total, message=f"page {idx}")

    log.info(
        "propose_regions: run=%s project=%s pages=%d proposals=%d",
        run_id, project.project_id, total, proposal_count,
    )


__all__ = ["handle_propose_regions"]
```

- [ ] **Step 6: Register the job type**

In `src/pdomain_ocr_labeler_spa/core/jobs/runner.py`, add a wrapper beside `_handle_refine_bboxes`:

```python
async def _handle_propose_regions(runner: JobRunner, job: Job) -> None:
    """propose_regions handler — delegates to ``core/jobs/handlers/propose_regions``.

    Book-scoped region proposal run. Never writes the page blob — see the handler's
    own docstring for the invariant it holds.
    """
    from .handlers.propose_regions import handle_propose_regions  # lazy import

    await handle_propose_regions(runner, job)
```

Add the entry to `_HANDLERS`:

```python
_HANDLERS: dict[str, Handler] = {
    "reload_ocr": _handle_reload_ocr,
    "save_project": _handle_save_project,
    "export": _handle_export,
    "rotate_page": _handle_rotate_page,
    "auto_rotate_all": _handle_auto_rotate_all,
    "refine_bboxes": _handle_refine_bboxes,
    "propose_regions": _handle_propose_regions,
}
```

- [ ] **Step 7: Add the book-scoped route**

In `src/pdomain_ocr_labeler_spa/api/regions.py`, add to imports:

```python
from ..core.jobs import JobRunner
from .dependencies import get_job_runner
```

Add request/response models beside `ListRegionProposalsResponse`:

```python
class StartRegionProposalRunRequest(BaseModel):
    """No page-kind fields: the handler reads that state itself from the page-kind
    stores (``PageKindProposalLog``, ``PageKindReviewedStore``) rather than trusting
    a caller's say-so — see the job handler's docstring.
    """

    model_id: str = "null-detector"
    model_version: str = "0.0.0"


class StartRegionProposalRunResponse(BaseModel):
    job_id: str
```

Add the route at the end of the file, before `install_regions_router`:

```python
@router.post(
    "/{project_id}/regions/propose",
    status_code=202,
    response_model=StartRegionProposalRunResponse,
    operation_id="start_region_proposal_run",
)
def start_region_proposal_run(
    project_id: str,
    body: StartRegionProposalRunRequest,
    project_state: ProjectState = Depends(get_project_state),
    runner: JobRunner = Depends(get_job_runner),
) -> JSONResponse:
    """Start a book-scoped proposal run. Progress and completion stream via ``/api/jobs``."""
    project = project_state.loaded_project
    if project is None or project.project_id != project_id:
        return JSONResponse(
            status_code=404,
            content=ApiError(error="project_not_found", message=f"project not found: {project_id}").model_dump(),
        )
    job_id = runner.submit("propose_regions", project_id=project_id, payload=body.model_dump())
    return JSONResponse(status_code=202, content={"job_id": job_id})
```

Add the two new request/response classes to `__all__`.

- [ ] **Step 8: Write the job-route and invariant tests**

Append to `tests/integration/test_region_proposals_router.py`:

```python
def test_start_proposal_run_returns_a_job_id(toolbar_loaded: Any) -> None:
    client, _ps, _page = toolbar_loaded
    r = client.post("/api/projects/book1/regions/propose", json={})
    assert r.status_code == 202, r.text
    assert r.json()["job_id"]


def test_start_proposal_run_on_unloaded_project_returns_404(toolbar_loaded: Any) -> None:
    client, _ps, _page = toolbar_loaded
    r = client.post("/api/projects/does-not-exist/regions/propose", json={})
    assert r.status_code == 404, r.text


def test_proposal_run_never_writes_the_page_blob(toolbar_loaded: Any, tmp_path: Path) -> None:
    """The invariant test: run a proposal job over a page, assert the blob is untouched.

    Marks page 0's kind reviewed first — the handler now reads page-kind state itself
    and skips any page lacking it, so an unmarked page would make this test vacuous.
    """
    import asyncio
    from datetime import UTC, datetime

    from pdomain_ocr_labeler_spa.core.page_kind.reviewed_store import PageKindReviewedStore

    client, project_state, _page = toolbar_loaded
    store = client.app.state.page_store
    runner = client.app.state.job_runner
    project = project_state.loaded_project
    assert project is not None
    PageKindReviewedStore(project.project_root).mark_reviewed(0, datetime.now(UTC).isoformat())

    pstate = project_state.page_states[0]
    agg_before = store.get_page(pstate.page_id)
    hash_before = (
        agg_before.record.provenance.head.blob_refs[0]
        if agg_before.record.provenance and agg_before.record.provenance.head
        else None
    )

    from pdomain_ocr_labeler_spa.core.jobs.handlers.propose_regions import handle_propose_regions
    from pdomain_ocr_labeler_spa.core.jobs.runner import Job, JobStatus

    job = Job(
        job_id="test-job",
        job_type="propose_regions",
        status=JobStatus.RUNNING,
        project_id=project.project_id,
        payload={},
        created_at=datetime.now(UTC),
    )
    runner._jobs[job.job_id] = job  # test-only direct enqueue, mirrors runner._run_one's bookkeeping
    asyncio.run(handle_propose_regions(runner, job))

    agg_after = store.get_page(pstate.page_id)
    hash_after = (
        agg_after.record.provenance.head.blob_refs[0]
        if agg_after.record.provenance and agg_after.record.provenance.head
        else None
    )
    assert hash_after == hash_before


def test_a_page_with_no_page_kind_state_gets_no_region_proposals(toolbar_loaded: Any) -> None:
    """The job reads page-kind state itself; an unproposed, unconfirmed page is skipped.

    No page in this fixture has a proposed or confirmed kind, so the run never even
    starts — nothing is written to the proposal journal.
    """
    import asyncio
    from datetime import UTC, datetime

    from pdomain_ocr_labeler_spa.core.jobs.handlers.propose_regions import handle_propose_regions
    from pdomain_ocr_labeler_spa.core.jobs.runner import Job, JobStatus
    from pdomain_ocr_labeler_spa.core.regions.proposal_log import RegionProposalLog

    client, project_state, _page = toolbar_loaded
    runner = client.app.state.job_runner
    project = project_state.loaded_project
    assert project is not None

    job = Job(
        job_id="test-job-2",
        job_type="propose_regions",
        status=JobStatus.RUNNING,
        project_id=project.project_id,
        payload={},
        created_at=datetime.now(UTC),
    )
    runner._jobs[job.job_id] = job
    asyncio.run(handle_propose_regions(runner, job))

    assert RegionProposalLog(project.project_root).runs() == []
```

- [ ] **Step 9: Run the tests**

Run: `uv run pytest tests/unit/core/regions/test_detector.py tests/integration/test_region_proposals_router.py -v`
Expected: PASS, all tests including the four new job/route tests.

- [ ] **Step 10: Regenerate the OpenAPI contract and run the full suite**

```bash
make openapi-export
make AI=1 test
```

Expected: `types.ts` picks up the final new route; full suite passes.

- [ ] **Step 11: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/core/regions/detector.py \
  src/pdomain_ocr_labeler_spa/core/jobs/handlers/propose_regions.py \
  src/pdomain_ocr_labeler_spa/core/jobs/runner.py src/pdomain_ocr_labeler_spa/api/regions.py \
  tests/unit/core/regions/test_detector.py tests/integration/test_region_proposals_router.py \
  frontend/src/api/types.ts
git commit -m "feat(regions): add the propose_regions job and its book-scoped route"
```

---

### Task 6: The conformance golden fixture

Pins `block_role_labels` and `override_page_sort_order` round-tripping through `Block.to_dict`/
`from_dict`, so a future `Block` change cannot quietly drop either — the property this whole design
leans on to justify storing regions as `Block` objects rather than a sidecar.

**Files:**

- Create: `tests/conformance/fixtures/region_block_round_trip.json`
- Create: `tests/conformance/test_region_block_round_trip.py`

**Interfaces:**

- Consumes: `Block.to_dict`, `Block.from_dict` from `pdomain_book_tools.ocr.block`.

- [ ] **Step 1: Write the golden fixture**

Create `tests/conformance/fixtures/region_block_round_trip.json`:

```json
{
  "type": "Block",
  "child_type": "WORDS",
  "block_category": "BLOCK",
  "block_labels": null,
  "block_role_labels": ["poetry"],
  "block_position_labels": [],
  "line_role_labels": [],
  "line_position_labels": [],
  "baseline": null,
  "bounding_box": {
    "top_left": {"x": 10, "y": 20, "is_normalized": false},
    "bottom_right": {"x": 300, "y": 400, "is_normalized": false},
    "is_normalized": false
  },
  "items": [],
  "override_page_sort_order": 3,
  "unmatched_ground_truth_words": [],
  "additional_block_attributes": {"region_id": "fixture-region-1"},
  "base_ground_truth_text": ""
}
```

- [ ] **Step 2: Write the failing conformance test**

Create `tests/conformance/test_region_block_round_trip.py`:

```python
"""Conformance: block_role_labels and override_page_sort_order round-trip on Block.

Pins the property the region-provenance design leans on to justify storing
confirmed regions as ``Block`` objects rather than a new sidecar: a role label
and an explicit sort order both survive ``to_dict`` / ``from_dict``. A future
``Block`` refactor that drops either field breaks this fixture, not a
downstream region test three layers away.
"""

from __future__ import annotations

import json
from pathlib import Path

_FIXTURE = Path(__file__).parent / "fixtures" / "region_block_round_trip.json"


def test_block_role_labels_and_sort_order_round_trip() -> None:
    from pdomain_book_tools.ocr.block import Block

    raw = json.loads(_FIXTURE.read_text())
    block = Block.from_dict(raw)

    assert block.block_role_labels == ["poetry"]
    assert block.override_page_sort_order == 3
    assert block.additional_block_attributes.get("region_id") == "fixture-region-1"

    round_tripped = Block.from_dict(block.to_dict())
    assert round_tripped.block_role_labels == ["poetry"]
    assert round_tripped.override_page_sort_order == 3
    assert round_tripped.additional_block_attributes.get("region_id") == "fixture-region-1"


def test_the_fixture_itself_matches_the_golden_bytes() -> None:
    """Guards the fixture file against silent hand-editing — re-serialize and diff."""
    from pdomain_book_tools.ocr.block import Block

    raw = json.loads(_FIXTURE.read_text())
    block = Block.from_dict(raw)
    dumped = block.to_dict()

    assert dumped["block_role_labels"] == raw["block_role_labels"]
    assert dumped["override_page_sort_order"] == raw["override_page_sort_order"]
    assert dumped["additional_block_attributes"] == raw["additional_block_attributes"]
```

- [ ] **Step 3: Run test to verify it fails, then passes**

Run: `uv run pytest tests/conformance/test_region_block_round_trip.py -v`
Expected: PASS immediately — `Block.to_dict`/`from_dict` already carry both fields (verified
directly against `pdomain-book-tools/pdomain_book_tools/ocr/block.py:1051-1160`). This is a golden
fixture, not a TDD red step: it exists to catch regression, not to drive new production code.

- [ ] **Step 4: Run the full suite**

Run: `make AI=1 test`
Expected: PASS. Conformance tests are not marker-excluded, so this file joins the existing two —
`test_new_contract.py` and `test_response_models.py` — as the third.

- [ ] **Step 5: Commit**

```bash
git add tests/conformance/fixtures/region_block_round_trip.json tests/conformance/test_region_block_round_trip.py
git commit -m "test(regions): pin block_role_labels and override_page_sort_order round-tripping"
```

---

### Task 7: The region layer on the canvas, and the Playwright visibility test

The one browser test that earns its cost: proposals must render visibly distinct from confirmed
regions, or the labeler risks treating model output as data. `BBoxOverlay.tsx` already has a
`"blocks"` layer with its own `LAYER_COLORS` entry — this task adds two more layers beside it rather
than building a new rendering system.

**Files:**

- Modify: `frontend/src/components/BBoxOverlay.tsx`
- Modify: `frontend/src/components/PageImageCanvas.tsx`
- Test: `tests/e2e/test_region_layer_visibility.py`

**Interfaces:**

- Consumes: `PagePayload.regions: list[RegionView]` (Task 1), each with `confirmed: bool`.
- Produces: `LayerName` gains `"regions-confirmed"` / `"regions-proposed"`; `PageImageCanvas`
  renders both from `page.regions`.

- [ ] **Step 1: Add the two layers to `BBoxOverlay.tsx`**

Read `frontend/src/components/BBoxOverlay.tsx` first. Extend the `LayerName` union:

```typescript
export type LayerName =
  | "blocks"
  | "paragraphs"
  | "lines"
  | "words"
  | "regions-confirmed"
  | "regions-proposed"
  | "drag-rect"
  | "selection-paragraphs"
  | "selection-lines"
  | "selection-words";
```

Add two entries to `LAYER_COLORS`, after `"blocks"`. Confirmed regions get a solid, saturated
amber close to the existing `"blocks"` treatment but visually heavier (thicker stroke, higher
opacity fill) so a person immediately reads them as decided; proposed regions get a cooler,
lighter, lower-opacity fill so they read as tentative — the two must differ in more than opacity
alone so a colorblind-safe screenshot diff (comparing hue, not just alpha) still tells them apart:

```typescript
  "regions-confirmed": {
    fill: "rgba(217,119,6,0.35)",
    stroke: "rgba(180,83,9,0.90)",
    strokeWidth: 2,
  },
  "regions-proposed": {
    fill: "rgba(14,165,233,0.15)",
    stroke: "rgba(3,105,161,0.55)",
    strokeWidth: 1,
  },
```

- [ ] **Step 2: Wire the region overlay items in `PageImageCanvas.tsx`**

Read `frontend/src/components/PageImageCanvas.tsx` first, focusing on `structuralOverlayItems` and
its two `useMemo` neighbors. Add a new memo beside `structuralOverlayItems`:

```typescript
  const regionOverlayItems = useMemo(() => {
    const regions = page?.regions ?? [];
    const toItem = (r: (typeof regions)[number]): BBoxItem => ({
      id: r.region_id ?? r.proposal_id ?? "",
      bbox: encoded ? rectToDisplay(r.box, encoded) : r.box,
    });
    return {
      confirmed: regions.filter((r) => r.confirmed).map(toItem),
      proposed: regions.filter((r) => !r.confirmed).map(toItem),
    };
  }, [page, encoded]);
```

In the selection-slot JSX block where the existing `<BBoxOverlay layer="blocks" .../>` and its
siblings render, add two more entries:

```tsx
              <BBoxOverlay
                layer="regions-confirmed"
                items={regionOverlayItems.confirmed}
                visible={layerVisibility.block}
              />
              <BBoxOverlay
                layer="regions-proposed"
                items={regionOverlayItems.proposed}
                visible={layerVisibility.block}
              />
```

(`layerVisibility.block` is reused rather than a new toggle — regions ride the existing "blocks"
visibility switch until slice 3 gives them their own rail entry.)

- [ ] **Step 3: Frontend build check**

Run: `cd frontend && npm run build`
Expected: builds clean, no TypeScript errors from the new `LayerName` members or the new memo.

- [ ] **Step 4: Write the failing Playwright test**

Create `tests/e2e/test_region_layer_visibility.py`:

```python
"""E2E: a confirmed region and a proposal render as visibly different colors.

The guard against treating model output as data — the split design's own
words. Seeds one confirmed region (a real Block with block_role_labels and a
region_id) and one proposal (via RegionProposalLog) on the same page, loads
it in a real browser, and samples two known screen points.
"""

from __future__ import annotations

import json
import socket
import struct
import threading
import time
import zlib
from collections.abc import Iterator
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import httpx
import pytest
import uvicorn
from pdomain_book_contracts.annotation import RegionRole
from pdomain_book_contracts.geometry.bounding_box import BoundingBox
from pdomain_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pdomain_book_tools.ocr.page import Page as BookPage
from PIL import Image
from playwright.sync_api import Page

from pdomain_ocr_labeler_spa.adapters.ocr.local_doctr import _ingest_ocr_result, _register_page_in_project
from pdomain_ocr_labeler_spa.bootstrap import build_app
from pdomain_ocr_labeler_spa.core.persistence.page_store import LabelerPageStore
from pdomain_ocr_labeler_spa.core.regions.models import ProposalRun, RegionProposal
from pdomain_ocr_labeler_spa.core.regions.proposal_log import RegionProposalLog
from pdomain_ocr_labeler_spa.settings import Settings
from tests.e2e.helpers import wait_for_project_ready

_PROJECT_ID = "region-visibility-fixture"
_IMAGE_W = 1200
_IMAGE_H = 1600
_CONFIRMED_LTRB = (100, 100, 400, 300)
_PROPOSED_LTRB = (100, 500, 400, 700)


def _spa_built() -> bool:
    static = Path(__file__).resolve().parents[2] / "src" / "pdomain_ocr_labeler_spa" / "static"
    return (static / "index.html").is_file()


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until(url: str, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if httpx.get(url, timeout=0.5).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    raise RuntimeError(f"Server did not become ready at {url!r} within {timeout}s")


def _make_png(width: int, height: int) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    raw = b"".join(bytes([0]) + bytes([255] * width) for _ in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def _sample_center(page: Page, ltrb: tuple[int, int, int, int], canvas_box: dict, fit_scale: float) -> tuple[int, int, int]:
    left, top, right, bottom = ltrb
    cx = int(canvas_box["x"] + (left + right) / 2 * fit_scale)
    cy = int(canvas_box["y"] + (top + bottom) / 2 * fit_scale)
    image = Image.open(BytesIO(page.screenshot(full_page=True))).convert("RGB")
    return image.getpixel((cx, cy))


@dataclass
class RegionServer:
    base_url: str


@pytest.fixture(scope="module")
def region_server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[RegionServer]:
    if not _spa_built():
        pytest.skip("SPA not built — run `make frontend-build` (or `make e2e`) first")

    data_root = tmp_path_factory.mktemp("region-data")
    cache_root = tmp_path_factory.mktemp("region-cache")
    config_root = tmp_path_factory.mktemp("region-config")
    source_root = tmp_path_factory.mktemp("region-source")

    dest = source_root / _PROJECT_ID
    dest.mkdir(parents=True)
    image_bytes = _make_png(_IMAGE_W, _IMAGE_H)
    (dest / "001.png").write_bytes(image_bytes)
    (dest / "pages.json").write_text(json.dumps({"001.png": ""}))

    confirmed_block = Block(
        items=[],
        bounding_box=BoundingBox.from_ltrb(*_CONFIRMED_LTRB, is_normalized=False),
        child_type=BlockChildType.WORDS,
        block_category=BlockCategory.BLOCK,
        block_role_labels=["poetry"],
        additional_block_attributes={"region_id": "confirmed-1"},
    )
    book_page = BookPage(width=_IMAGE_W, height=_IMAGE_H, page_index=0, blocks=[confirmed_block])

    store = LabelerPageStore(dest)
    try:
        _ingest_ocr_result(page=book_page, image_bytes=image_bytes, page_index=0, store=store)
        _register_page_in_project(store=store, project_id=_PROJECT_ID, page_id=book_page.page_id, page_index=0)

        proposal_log = RegionProposalLog(dest)
        proposal_log.append_run(
            ProposalRun(
                run_id="r1",
                model_id="fixture-detector",
                model_version="0.0.0",
                created_at="2026-09-08T10:00:00+00:00",
                page_facet_digests={},
                depends_on=frozenset(),
                page_kind_decision_ref=None,
                page_kind_was_confirmed=False,
            )
        )
        proposal_log.append_proposals(
            [
                RegionProposal(
                    proposal_id="proposed-1",
                    run_id="r1",
                    page_index=0,
                    role=RegionRole.BLOCKQUOTE,
                    box=_PROPOSED_LTRB,
                    confidence=0.6,
                    evidence={"signal": "indent"},
                )
            ]
        )
    finally:
        store.close()

    port = _pick_free_port()
    settings = Settings(
        host="127.0.0.1", port=port, data_root=data_root, cache_root=cache_root, config_root=config_root,
        source_projects_root=source_root, mode="normal",
    )
    app = build_app(settings)
    config = uvicorn.Config(app, host=settings.host, port=settings.port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://{settings.host}:{settings.port}"
    try:
        _wait_until(f"{base_url}/healthz")
    except RuntimeError:
        server.should_exit = True
        thread.join(timeout=2)
        raise

    r = httpx.post(f"{base_url}/api/projects/source-root", json={"path": str(source_root)}, timeout=10)
    assert r.status_code in (200, 204), f"source-root POST failed: {r.status_code} {r.text}"
    r = httpx.post(f"{base_url}/api/projects/load", json={"project_root": str(dest)}, timeout=30)
    assert r.status_code == 200, f"load project failed: {r.status_code} {r.text}"

    yield RegionServer(base_url=base_url)

    server.should_exit = True
    thread.join(timeout=5)


@pytest.mark.e2e
def test_a_proposed_region_renders_a_different_color_than_a_confirmed_one(
    region_server: RegionServer,
    page: Page,
) -> None:
    resp = httpx.get(f"{region_server.base_url}/api/projects/{_PROJECT_ID}/pages/0", timeout=10.0)
    assert resp.status_code == 200, f"page payload GET failed: {resp.status_code}"
    payload = resp.json()
    encoded = payload["encoded_dims"]
    assert encoded is not None
    regions = payload["regions"]
    assert any(r["confirmed"] and r["region_id"] == "confirmed-1" for r in regions)
    assert any(not r["confirmed"] and r["proposal_id"] == "proposed-1" for r in regions)

    page.goto(f"{region_server.base_url}/projects/{_PROJECT_ID}/pages/pageno/1", timeout=20_000)
    page.wait_for_selector('[data-testid="project-page"]', timeout=20_000)
    wait_for_project_ready(page)

    viewport = page.locator('[data-testid="image-viewport"]').first
    viewport.wait_for(state="visible", timeout=10_000)
    stage_canvas = viewport.locator("canvas").first
    stage_canvas.wait_for(state="visible", timeout=10_000)
    canvas_box = stage_canvas.bounding_box()
    assert canvas_box is not None
    fit_scale = canvas_box["width"] / encoded["display_width"]

    confirmed_pixel = _sample_center(page, _CONFIRMED_LTRB, canvas_box, fit_scale)
    proposed_pixel = _sample_center(page, _PROPOSED_LTRB, canvas_box, fit_scale)
    white = (255, 255, 255)

    assert confirmed_pixel != white, f"confirmed region did not paint: {confirmed_pixel}"
    assert proposed_pixel != white, f"proposed region did not paint: {proposed_pixel}"
    assert confirmed_pixel != proposed_pixel, (
        f"confirmed and proposed regions rendered the same color: {confirmed_pixel} == {proposed_pixel} "
        "— they must be visibly distinct or model output risks being treated as data"
    )
```

- [ ] **Step 5: Run the test to verify it fails**

Run: `make frontend-build && uv run --group e2e pytest tests/e2e/test_region_layer_visibility.py -v --browser chromium`
Expected: FAIL before Steps 1-2 are applied (regions never paint, both samples are white); PASS
once the layers and the memo are wired.

- [ ] **Step 6: Run the full e2e suite**

Run: `make e2e`
Expected: PASS, no regressions in the other 24 Playwright files.

- [ ] **Step 7: Final full gate**

```bash
make AI=1 ci
```

Expected: PASS end to end — setup, pre-commit, format-check, typecheck, test, build.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/BBoxOverlay.tsx frontend/src/components/PageImageCanvas.tsx \
  tests/e2e/test_region_layer_visibility.py
git commit -m "feat(regions): render proposals visibly distinct from confirmed regions"
```

---

## What this plan does not do

- It does not compute real proposals. `null_region_detector` is the only detector wired; the
  geometry engine that turns `typography.json` and PP-DocLayout into proposals is slice 4, on a
  page-template spread this plan does not touch.
- It does not widen `Block.ALLOWED_BLOCK_ROLE_LABELS` to the full 34-value `RegionRole`
  vocabulary. That is a `pdomain-book-tools` change, out of this plan's repo scope; until it
  lands, 14 of the 34 roles return `400 invalid_region_role` from every route in this plan.
- It does not cascade edit or delete to a container region's nested children. Deleting a
  `child_type="blocks"` region recovers its descendant words (via `Block.words`, which already
  recurses) but does not orphan-repair or re-home nested child region blocks; that is left for
  whoever builds the review UI's nesting affordance in slice 3.
- It does not add `BlockCategory.GROUP` or widen role support to `brace`/`bracket`/`group
  label`/`page header`. `BlockCategory` stays at `BLOCK`/`PARAGRAPH`/`LINE`, same as
  `Block.ALLOWED_BLOCK_ROLE_LABELS` staying at 20 values above; both are dependencies on the
  preconditions plan.
- It does not add a page-kind classifier, a confidence review queue, or any agent-specific
  affordance beyond what these eight routes and `PagePayload` already carry — those are slices 1,
  5, and 6. It does read page-kind state (Task 5's job handler), but only to gate which pages get
  proposed over; it never writes page kind.
- It does not cache the proposal or decision journals. `_page_payload` re-scans both JSONL files
  on every request; that is acceptable at slice-2 scale and unoptimized on purpose.
- It does not give regions their own rail-visibility toggle. The new canvas layers ride the
  existing "blocks" visibility switch until slice 3 builds the review UI.
- It does not touch style spans, word provenance, or glyph annotations — those ride on
  `ReviewMetadata.source` from the first plan and are untouched here.
- It does not implement the geometric matching that produces a `Disposition.CARRIED` decision.
  That belongs to slice 4's proposal engine, same as the corresponding boundary in the stores plan.

## Related

- [Annotation provenance and
  persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md) — the design.
- [Region stores and resolver](2026-09-08-region-stores-and-resolver.md) — the first half of slice
  2; this plan consumes its models, journals, and resolver directly.
- [Annotation vocabularies in
  book-contracts](2026-09-08-annotation-vocabularies-in-book-contracts.md) — `RegionRole` and
  `KnowledgeState` must land first.
- [Annotation preconditions in book-tools and
  measure](2026-09-08-annotation-preconditions-in-book-tools-and-measure.md) — confirms
  `Block.ALLOWED_BLOCK_ROLE_LABELS` stays at 20 values; this plan's `invalid_region_role` handling
  is the direct consequence. Also where `BlockCategory.GROUP` and the four group-shaped roles this
  plan cannot yet build (`brace`, `bracket`, `group label`, `page header`) would need to land.
- [Page kind, end to end](2026-09-08-page-kind-end-to-end.md) — `PageKindProposalLog` and
  `PageKindReviewedStore` must land first; Task 5's job handler reads both directly rather than
  trusting a caller-supplied page-kind reference.
- [Labeling track roadmap](2026-09-07-labeling-track-roadmap.md) — the seven slices; slice 3
  (region review UI) and slice 4 (the proposal engine) build on this plan.
