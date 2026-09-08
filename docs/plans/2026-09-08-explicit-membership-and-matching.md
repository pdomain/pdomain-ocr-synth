# Explicit Membership and Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop treating geometric containment as region membership. In `pdomain-book-tools`, turn the
word-tagging pass that currently writes a `layout:<type>` label for every region a word's centre
falls in into a proposal generator that also names which candidate is the innermost and which
words are genuinely disputed between siblings, and add the block-tree invariant that no word is
reachable from two sibling regions. In `pdomain-ocr-labeler-spa`, add the geometry-only matcher that
finds which proposal a confirmed region came from, on page and box, never on list position or
ordinal.

**Architecture:** Two independent repos, three tasks. `tag_words_with_layout` keeps its existing
side effect (writing a tag for every candidate region a word's centre falls in) so the two existing
consumers of that tag — the figure-internal-noise drop pass and the block-role bubble-up — see no
behaviour change. What changes is that the same per-word geometry is now exposed as a typed,
pure proposal list, so a caller can tell an unambiguous single-owner candidate from a genuine
sibling tie the rectangle test cannot break. The sibling-disjointness check is a second, independent
addition: it walks the confirmed block tree built by `reorganize_page`, not the geometric proposals,
and reports a word signature reachable from more than one block at the same tree level. The matcher
in the labeler is unrelated to either book-tools change; it consumes `RegionProposal` and
`ResolvedRegion` records already defined by a separate plan and picks the best-overlapping proposal
for a confirmed region using the IoU helper that already exists in `pdomain-book-contracts`.

**Tech Stack:** book-tools — Python `>=3.11,<3.14`, pytest, ruff, basedpyright. labeler-spa — Python
`>=3.13,<3.14`, frozen dataclasses, pytest, ruff, basedpyright.

**Spec:** [Annotation provenance and
persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md), section "Reading
order follows explicit membership, not geometry" and "A region is identified by its geometry, never
by its position in a list".

## Agent Index

- **Kind:** plan
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-08
- **Last verified:** 2026-09-08
- **Provenance:** authored 2026-09-08 from the design spec above and direct inspection of
  `pdomain-book-tools` `pdomain_book_tools/ocr/layout_aware_reorg.py`,
  `pdomain_book_tools/ocr/reorganize_page_utils.py`, `pdomain_book_tools/ocr/block.py`,
  `pdomain_book_tools/ocr/page.py`, `pdomain_book_tools/layout/geometry.py`,
  `pdomain_book_tools/layout/types.py`, and `tests/layout/test_layout_aware_reorg.py`;
  `pdomain-book-contracts` `pdomain_book_contracts/layout/types.py` and
  `pdomain_book_contracts/layout/regions.py`; and `pdomain-ocr-labeler-spa` `pyproject.toml`,
  `Makefile`, and its installed `pdomain_book_contracts==0.1.0` package.
- **Disposition:** Active. Task 2 depends on `find_duplicated_words` from the annotation-preconditions
  plan's Task 1 already being released. Task 3 depends on `RegionProposal` / `ResolvedRegion` from
  the region-stores-and-resolver plan's Task 1, and on `RegionRole` from the
  annotation-vocabularies-in-book-contracts plan, both already released.
- **Read when:** implementing explicit word-region membership, the sibling-disjointness invariant, or
  the geometry-based proposal-to-region matcher.
- **Search terms:** tag_words_with_layout, propose_word_regions, WordRegionProposal, sibling regions
  disjoint, find_words_in_multiple_sibling_regions, match_proposal_to_region, IoU matching, region
  identity by page and box, ragged figure notch.

## Global Constraints

- **book-tools:** Python `>=3.11,<3.14`. `filterwarnings = ["error"]`, `--strict-markers`,
  `--strict-config`. Branch coverage is on. Run targets with `AI=1` to capture verbose output to
  `.ci-ai.log`. Run `make ci AI=1` before committing.
- **labeler-spa:** Python `>=3.13,<3.14`. Warnings are errors. Run `make AI=1 ci` before committing;
  its `ci` target includes `typecheck`, so basedpyright runs on every change.
- **Geometry only proposes membership; nothing in this plan stores confirmed membership.** The
  route that lets a person set a region's word membership as an explicit edge is the fourth
  (routes) plan, which this plan does not touch.
- **Region and proposal identity is never positional.** Task 3's matcher takes proposals already
  scoped to one page by its caller and matches purely on box overlap — never on where a proposal
  sits in the sequence, and never on a line or word ordinal.
- **`tag_words_with_layout`'s existing side effect must not change.** It writes a `layout:<type>`
  label for every region a word's centre falls in, and `drop_figure_internal_words`
  (`_word_has_only_layout_tag` at `pdomain_book_tools/ocr/layout_aware_reorg.py:366`) depends on a
  word carrying more than one `layout:*` tag to tell wrap-around body text apart from
  figure-internal noise. Silently narrowing that tag set disables that drop pass.
- `find_duplicated_words` and `raise_if_words_duplicated` in
  `pdomain_book_tools/ocr/reorganize_page_utils.py`, added by the annotation-preconditions plan's
  Task 1, must already be released before Task 2 starts. Task 2 wires its own check in immediately
  after that plan's, inside `reconcile_dropped_words`.
- `RegionProposal` and `ResolvedRegion` come from `pdomain_ocr_labeler_spa.core.regions.models`,
  added by the region-stores-and-resolver plan's Task 1. `RegionRole` comes from
  `pdomain_book_contracts.annotation`, added by the annotation-vocabularies-in-book-contracts plan.
  Both must already be released before Task 3 starts.

---

## File Structure

| file | responsibility |
| --- | --- |
| `pdomain_book_tools/ocr/layout_aware_reorg.py` | modified: proposal generator; `tag_words_with_layout` rebuilt on it |
| `pdomain-book-tools/tests/layout/test_layout_aware_reorg.py` | proposal generator coverage; tagging unchanged |
| `pdomain_book_tools/ocr/reorganize_page_utils.py` | modified: sibling-disjointness check, wired into reconcile |
| `pdomain-book-tools/tests/ocr/test_sibling_region_membership.py` | sibling-disjointness invariant and strict mode |
| `src/pdomain_ocr_labeler_spa/core/regions/matcher.py` | `match_proposal_to_region`, the proposal-to-region matcher |
| `pdomain-ocr-labeler-spa/tests/unit/core/regions/test_matcher.py` | the matcher's resolution table |

---

### Task 1: The word-region proposal generator (book-tools)

`tag_words_with_layout` currently writes a `layout:<type>` label onto `word.word_labels` for every
region whose rectangle contains the word's bounding-box centre, with no signal about which
candidate is more specific. Containment is a plain axis-aligned test — `L <= x <= R and T <= y <= B`
— so body text flowing around a ragged figure sits in the notch of the figure's bounding rectangle
and tests as inside the figure even though it plainly is not figure content. That is what the
existing multi-tag output actually is: a set of candidates, not a resolved answer, and nothing in
the code says so today.

This task extracts the per-word geometry into a pure function that says which candidates exist,
which one is innermost when the candidates nest cleanly, and which words are genuinely disputed —
two or more candidates where neither's box contains the other's, which is exactly the ragged-notch
case. `tag_words_with_layout` is rebuilt on top of it and keeps writing a tag for every candidate,
disputed or not, so its existing consumers see no behaviour change.

**Files:**

- Modify: `pdomain_book_tools/ocr/layout_aware_reorg.py`
- Test: `pdomain-book-tools/tests/layout/test_layout_aware_reorg.py`

**Interfaces:**

- Consumes: `contains` from `pdomain_book_tools.layout.geometry` (already re-exports
  `pdomain_book_contracts.layout.regions.contains`); `_word_bbox_in_layout_frame`,
  `_word_center_in_region`, `_resolve_dimensions`, `DEFAULT_TAG_CONFIDENCE`, all already in this
  module.
- Produces: `WordRegionProposal` (frozen dataclass) and `propose_word_regions(...)`, with this
  signature:

```python
def propose_word_regions(
    page: Page,
    layout: PageLayout | None,
    confidence_threshold: float = DEFAULT_TAG_CONFIDENCE,
) -> list[WordRegionProposal]: ...
```

`tag_words_with_layout`'s signature and return contract (`int`, the count tagged) are unchanged.

- [ ] **Step 1: Write the failing test**

Add to `pdomain-book-tools/tests/layout/test_layout_aware_reorg.py`. First, add `WordRegionProposal`
and `propose_word_regions` to the existing import from `pdomain_book_tools.ocr.layout_aware_reorg`
(the block starting at line 19):

```python
from pdomain_book_tools.ocr.layout_aware_reorg import (
    _LEFT_SIDENOTE_SORT_ORDER,
    _RIGHT_SIDENOTE_SORT_ORDER,
    WordRegionProposal,
    associate_captions,
    bubble_block_roles_from_layout,
    detect_geometric_sidenotes,
    drop_figure_internal_words,
    drop_layout_regions,
    emit_caption_block,
    propose_word_regions,
    route_sidenote_reading_order,
    tag_words_with_layout,
    word_layout_tags,
    words_inside,
)
```

Then append this class at the end of the file, after `TestAssociateCaptionsDuplication`:

```python
class TestProposeWordRegions:
    def test_a_single_containing_region_is_unambiguous(self) -> None:
        words = [_word("hi", 100, 100, 200, 130)]
        page = _make_page([_paragraph_block([_line_block(words)])])
        layout = PageLayout(
            regions=[
                LayoutRegion(type=RegionType.text, L=0, R=400, T=50, B=200, confidence=0.9),
            ],
            image_width=PAGE_W,
            image_height=PAGE_H,
            detector="test",
        )
        proposals = propose_word_regions(page, layout)
        assert len(proposals) == 1
        assert proposals[0].region_type is RegionType.text
        assert proposals[0].is_innermost is True
        assert proposals[0].ambiguous is False

    def test_a_nested_region_is_the_innermost_candidate(self) -> None:
        # Figure occupies the whole lower half of the page; caption is fully
        # inside the figure's box, the way a caption strip sits inside its
        # figure column.
        words = [_word("Fig. 1", 150, 650, 250, 700)]
        page = _make_page([_paragraph_block([_line_block(words)])])
        layout = PageLayout(
            regions=[
                LayoutRegion(type=RegionType.figure, L=0, R=1000, T=0, B=800, confidence=0.9),
                LayoutRegion(type=RegionType.caption, L=100, R=400, T=600, B=750, confidence=0.9),
            ],
            image_width=PAGE_W,
            image_height=PAGE_H,
            detector="test",
        )
        proposals = propose_word_regions(page, layout)
        assert len(proposals) == 2
        by_type = {p.region_type: p for p in proposals}
        assert by_type[RegionType.caption].is_innermost is True
        assert by_type[RegionType.caption].ambiguous is False
        assert by_type[RegionType.figure].is_innermost is False
        assert by_type[RegionType.figure].ambiguous is False

    def test_sibling_overlap_marks_every_candidate_ambiguous(self) -> None:
        # Neither box contains the other -- the ragged-notch case: body text
        # sits where a figure's bounding rectangle and a text block's
        # rectangle both claim the same ground.
        words = [_word("wrap", 450, 100, 550, 130)]
        page = _make_page([_paragraph_block([_line_block(words)])])
        layout = PageLayout(
            regions=[
                LayoutRegion(type=RegionType.figure, L=0, R=600, T=0, B=600, confidence=0.9),
                LayoutRegion(type=RegionType.text, L=400, R=1000, T=0, B=600, confidence=0.9),
            ],
            image_width=PAGE_W,
            image_height=PAGE_H,
            detector="test",
        )
        proposals = propose_word_regions(page, layout)
        assert len(proposals) == 2
        assert all(p.ambiguous for p in proposals)
        assert all(p.is_innermost for p in proposals)

    def test_no_layout_returns_nothing(self) -> None:
        words = [_word("hi", 100, 100, 200, 130)]
        page = _make_page([_paragraph_block([_line_block(words)])])
        assert propose_word_regions(page, None) == []

    def test_does_not_mutate_the_word(self) -> None:
        words = [_word("hi", 100, 100, 200, 130)]
        page = _make_page([_paragraph_block([_line_block(words)])])
        layout = PageLayout(
            regions=[LayoutRegion(type=RegionType.text, L=0, R=400, T=50, B=200, confidence=0.9)],
            image_width=PAGE_W,
            image_height=PAGE_H,
            detector="test",
        )
        propose_word_regions(page, layout)
        assert words[0].word_labels == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `make test-single TEST='tests/layout/test_layout_aware_reorg.py::TestProposeWordRegions'`
Expected: FAIL with `ImportError: cannot import name 'propose_word_regions'`

- [ ] **Step 3: Write the implementation**

In `pdomain_book_tools/ocr/layout_aware_reorg.py`, add `dataclass` to the existing `typing`/stdlib
import block and `contains` to the existing `pdomain_book_tools.layout.geometry` import:

```python
from dataclasses import dataclass
```

```python
from pdomain_book_tools.layout.geometry import caption_for_figure, contains
```

Then, directly after `_layout_label` and before `tag_words_with_layout` (which currently starts at
line 218), add:

```python
@dataclass(frozen=True)
class WordRegionProposal:
    """One region a word's geometry proposes it might belong to.

    Word identity is the word's own bounding box, not a runtime id or list
    position -- the same rule region identity follows elsewhere in this
    design. ``is_innermost`` marks a proposal as the most specific candidate
    among everything whose rectangle contains this word; ``ambiguous`` is
    True when two or more candidates are equally specific, so a bounding-box
    test alone cannot name a single owner.
    """

    word_box: tuple[float, float, float, float]
    region_type: RegionType
    region_box: tuple[int, int, int, int]
    confidence: float
    is_innermost: bool
    ambiguous: bool


def propose_word_regions(
    page: Page,
    layout: PageLayout | None,
    confidence_threshold: float = DEFAULT_TAG_CONFIDENCE,
) -> list[WordRegionProposal]:
    """Propose which regions each word's geometry might belong to.

    Containment is a rectangle test against the word's bounding-box centre,
    so every result here is a hint, never a decision -- a region's box is not
    its membership. Where a word's candidate regions nest cleanly (one
    candidate's box sits fully inside another's, via :func:`contains`), the
    innermost candidate is unambiguous. Where two or more candidates share
    the word and neither contains the other -- body text flowing around a
    ragged figure sits in the notch of the figure's bounding rectangle, so it
    tests as inside both the figure and the text block beside it -- every
    candidate for that word is marked ``ambiguous``, because rectangle
    geometry cannot break that tie. Only ancestry in a confirmed block tree
    can, and that happens only after a person acts.

    Does not mutate ``page`` or any ``Word``. :func:`tag_words_with_layout`
    is the existing side-effecting caller built on this function; it still
    writes a ``layout:*`` label for every candidate returned here, disputed
    or not, matching its behaviour from before this function existed.
    """
    proposals: list[WordRegionProposal] = []
    if layout is None or not layout.regions:
        return proposals
    page_w, page_h = _resolve_dimensions(page)
    if page_w <= 0 or page_h <= 0:
        return proposals
    layout_w = float(layout.image_width or page_w)
    layout_h = float(layout.image_height or page_h)
    relevant = [r for r in layout.regions if r.confidence >= confidence_threshold]
    if not relevant:
        return proposals

    for word in page.words:
        proposals.extend(
            _propose_regions_for_word(
                word,
                relevant,
                page_w=page_w,
                page_h=page_h,
                layout_w=layout_w,
                layout_h=layout_h,
            )
        )
    return proposals


def _propose_regions_for_word(
    word: Word,
    relevant: list[LayoutRegion],
    *,
    page_w: float,
    page_h: float,
    layout_w: float,
    layout_h: float,
) -> list[WordRegionProposal]:
    coords = _word_bbox_in_layout_frame(word, page_w, page_h, layout_w, layout_h)
    if coords is None:
        return []
    candidates = [
        r
        for r in relevant
        if _word_center_in_region(
            word, r, page_w=page_w, page_h=page_h, layout_w=layout_w, layout_h=layout_h
        )
    ]
    if not candidates:
        return []
    # Minimal elements of the containment partial order are the innermost
    # candidates: a candidate is dominated when another candidate's box sits
    # inside it.
    minimal_ids = {
        id(r)
        for r in candidates
        if not any(other is not r and contains(outer=r, inner=other) for other in candidates)
    }
    ambiguous = len(minimal_ids) != 1
    return [
        WordRegionProposal(
            word_box=coords,
            region_type=region.type,
            region_box=(region.L, region.T, region.R, region.B),
            confidence=region.confidence,
            is_innermost=id(region) in minimal_ids,
            ambiguous=ambiguous,
        )
        for region in candidates
    ]
```

Now rebuild `tag_words_with_layout` on the shared helper. Replace its body (keep the docstring and
signature unchanged) with:

```python
def tag_words_with_layout(
    page: Page,
    layout: PageLayout | None,
    confidence_threshold: float = DEFAULT_TAG_CONFIDENCE,
) -> int:
    """Annotate each Word's ``word_labels`` with the layout regions it sits in.

    Tag format: ``"layout:<region_type>"`` (e.g. ``"layout:caption"``).
    Words can be inside more than one region (caption nested inside a
    figure column, etc.), in which case multiple tags are added.

    Returns the number of (word, region) pairs tagged. Idempotent — running
    twice with the same layout yields the same tags (duplicates skipped).

    Built on :func:`propose_word_regions`; writes a tag for every candidate
    it returns, disputed or not. This function has always been a hint for
    the geometric reorg pipeline, never a source of confirmed membership —
    see :func:`propose_word_regions` for the typed proposal shape a caller
    that needs to tell a disputed candidate from a resolved one should use
    instead.
    """
    if layout is None or not layout.regions:
        return 0
    page_w, page_h = _resolve_dimensions(page)
    if page_w <= 0 or page_h <= 0:
        logger.debug("tag_words_with_layout: page dims unknown; skipping")
        return 0
    layout_w = float(layout.image_width or page_w)
    layout_h = float(layout.image_height or page_h)

    relevant = [r for r in layout.regions if r.confidence >= confidence_threshold]
    if not relevant:
        return 0

    tagged = 0
    for word in page.words:
        for proposal in _propose_regions_for_word(
            word,
            relevant,
            page_w=page_w,
            page_h=page_h,
            layout_w=layout_w,
            layout_h=layout_h,
        ):
            label = _layout_label(proposal.region_type)
            if label not in word.word_labels:
                word.word_labels.append(label)
                tagged += 1
    return tagged
```

Finally, add the two new public names to `__all__` (alphabetical, matching the existing order):

```python
__all__ = [
    "DEFAULT_TAG_CONFIDENCE",
    "LAYOUT_LABEL_PREFIX",
    "WordRegionProposal",
    "associate_captions",
    "bubble_block_roles_from_layout",
    "detect_geometric_sidenotes",
    "drop_figure_internal_words",
    "drop_layout_regions",
    "emit_caption_block",
    "propose_word_regions",
    "route_sidenote_reading_order",
    "tag_words_with_layout",
    "word_layout_tags",
    "words_inside",
]
```

- [ ] **Step 4: Run the tests**

Run: `make test-single TEST='tests/layout/test_layout_aware_reorg.py::TestProposeWordRegions'`
Expected: PASS, all five tests.

- [ ] **Step 5: Run the whole file to confirm the tagging side effect is unchanged**

Run: `make test-single TEST='tests/layout/test_layout_aware_reorg.py'`
Expected: PASS, every existing class including `TestTagWordsWithLayout` and
`TestDropFigureInternalWords` — the latter is the regression guard for the multi-tag behaviour this
refactor must not touch.

- [ ] **Step 6: Commit**

```bash
git add pdomain_book_tools/ocr/layout_aware_reorg.py tests/layout/test_layout_aware_reorg.py
git commit -m "feat(layout): expose word-region candidacy as typed proposals"
```

---

### Task 2: The sibling-disjointness invariant (book-tools)

`validate_word_preservation` reports missing words and explicitly permits extras — correct while a
word could belong to several regions at once. Now that membership is meant to be explicit,
`find_duplicated_words` (from the annotation-preconditions plan) catches a word the pipeline
duplicated anywhere on the page. This task adds the narrower, structural check the design also
calls for: within any set of sibling blocks in the confirmed tree `reorganize_page` builds, no word
signature may be reachable from more than one sibling. A word reachable from a block and that
block's own ancestor is not a violation — a caption nested inside its parent figure block sharing
words with it is exactly what nesting means.

**Files:**

- Modify: `pdomain_book_tools/ocr/reorganize_page_utils.py`
- Test: `pdomain-book-tools/tests/ocr/test_sibling_region_membership.py`

**Interfaces:**

- Consumes: `collect_word_signatures`, `Block`, `BlockChildType`, `Word`,
  `reorganize_strict_mode_enabled`, all already in this module; depends on `find_duplicated_words`
  and `raise_if_words_duplicated` from the annotation-preconditions plan's Task 1 already being wired
  into `reconcile_dropped_words`.
- Produces: `find_words_in_multiple_sibling_regions(blocks: list[Block]) -> list[str]`,
  `ReorganizeSiblingMembershipError`, and
  `raise_if_words_in_multiple_siblings(blocks: list[Block], *, strict: bool) -> list[str]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/ocr/test_sibling_region_membership.py
from __future__ import annotations

import pytest

from pdomain_book_tools.geometry.bounding_box import BoundingBox
from pdomain_book_tools.geometry.point import Point
from pdomain_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pdomain_book_tools.ocr.word import Word


def _bbox(left: float, top: float, right: float, bottom: float) -> BoundingBox:
    return BoundingBox(
        top_left=Point(left, top, is_normalized=True),
        bottom_right=Point(right, bottom, is_normalized=True),
        is_normalized=True,
    )


def _word(text: str, left: float, top: float, right: float, bottom: float) -> Word:
    return Word(text=text, bounding_box=_bbox(left, top, right, bottom), ocr_confidence=0.95)


def _line(words: list[Word]) -> Block:
    return Block(items=words, child_type=BlockChildType.WORDS, block_category=BlockCategory.LINE)


def _paragraph(lines: list[Block]) -> Block:
    return Block(
        items=lines, child_type=BlockChildType.BLOCKS, block_category=BlockCategory.PARAGRAPH
    )


def test_a_single_block_reports_nothing() -> None:
    from pdomain_book_tools.ocr.reorganize_page_utils import (
        find_words_in_multiple_sibling_regions,
    )

    alpha = _word("alpha", 0.1, 0.1, 0.2, 0.2)
    blocks = [_paragraph([_line([alpha])])]
    assert find_words_in_multiple_sibling_regions(blocks) == []


def test_disjoint_siblings_report_nothing() -> None:
    from pdomain_book_tools.ocr.reorganize_page_utils import (
        find_words_in_multiple_sibling_regions,
    )

    alpha = _word("alpha", 0.1, 0.1, 0.2, 0.2)
    beta = _word("beta", 0.3, 0.1, 0.4, 0.2)
    blocks = [_paragraph([_line([alpha])]), _paragraph([_line([beta])])]
    assert find_words_in_multiple_sibling_regions(blocks) == []


def test_a_word_in_two_top_level_siblings_is_reported() -> None:
    from pdomain_book_tools.ocr.reorganize_page_utils import (
        find_words_in_multiple_sibling_regions,
    )

    alpha_a = _word("alpha", 0.1, 0.1, 0.2, 0.2)
    alpha_b = _word("alpha", 0.1, 0.1, 0.2, 0.2)
    blocks = [_paragraph([_line([alpha_a])]), _paragraph([_line([alpha_b])])]
    errors = find_words_in_multiple_sibling_regions(blocks)
    assert len(errors) == 1
    assert "alpha" in errors[0]
    assert "sibling" in errors[0]


def test_a_word_shared_with_its_own_ancestor_is_not_reported() -> None:
    from pdomain_book_tools.ocr.reorganize_page_utils import (
        find_words_in_multiple_sibling_regions,
    )

    caption_word = _word("caption", 0.1, 0.1, 0.2, 0.2)
    caption = _paragraph([_line([caption_word])])
    figure = Block(
        items=[caption],
        child_type=BlockChildType.BLOCKS,
        block_category=BlockCategory.BLOCK,
        block_role_labels=["illustration"],
    )
    assert find_words_in_multiple_sibling_regions([figure]) == []


def test_a_violation_nested_two_levels_deep_is_still_found() -> None:
    from pdomain_book_tools.ocr.reorganize_page_utils import (
        find_words_in_multiple_sibling_regions,
    )

    shared_a = _word("shared", 0.5, 0.5, 0.6, 0.6)
    shared_b = _word("shared", 0.5, 0.5, 0.6, 0.6)
    left_column = _paragraph([_line([shared_a])])
    right_column = _paragraph([_line([shared_b])])
    page_block = Block(
        items=[left_column, right_column],
        child_type=BlockChildType.BLOCKS,
        block_category=BlockCategory.BLOCK,
    )
    errors = find_words_in_multiple_sibling_regions([page_block])
    assert len(errors) == 1
    assert "shared" in errors[0]


def test_strict_mode_raises_on_a_violation() -> None:
    from pdomain_book_tools.ocr.reorganize_page_utils import (
        ReorganizeSiblingMembershipError,
        raise_if_words_in_multiple_siblings,
    )

    alpha_a = _word("alpha", 0.1, 0.1, 0.2, 0.2)
    alpha_b = _word("alpha", 0.1, 0.1, 0.2, 0.2)
    blocks = [_paragraph([_line([alpha_a])]), _paragraph([_line([alpha_b])])]
    with pytest.raises(ReorganizeSiblingMembershipError, match="1 sibling"):
        raise_if_words_in_multiple_siblings(blocks, strict=True)


def test_non_strict_mode_returns_the_errors_without_raising() -> None:
    from pdomain_book_tools.ocr.reorganize_page_utils import (
        raise_if_words_in_multiple_siblings,
    )

    alpha_a = _word("alpha", 0.1, 0.1, 0.2, 0.2)
    alpha_b = _word("alpha", 0.1, 0.1, 0.2, 0.2)
    blocks = [_paragraph([_line([alpha_a])]), _paragraph([_line([alpha_b])])]
    errors = raise_if_words_in_multiple_siblings(blocks, strict=False)
    assert len(errors) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `make test-single TEST='tests/ocr/test_sibling_region_membership.py'`
Expected: FAIL with `ImportError: cannot import name 'find_words_in_multiple_sibling_regions'`

- [ ] **Step 3: Write the implementation**

Add `Iterator` to the `TYPE_CHECKING` import block at the top of
`pdomain_book_tools/ocr/reorganize_page_utils.py`:

```python
if TYPE_CHECKING:
    from collections.abc import Iterator

    from pdomain_book_tools.ocr.page import Page
```

Then add this, directly after `raise_if_words_duplicated` (the annotation-preconditions plan's
Task 1 addition, itself directly after `find_duplicated_words`):

```python
def _all_word_signatures_in_block(
    block: Block,
) -> set[tuple[str, float, float, float, float]]:
    """Recursively collect every word signature reachable from ``block``."""
    if block.child_type == BlockChildType.WORDS:
        return set(
            collect_word_signatures([item for item in block.items if isinstance(item, Word)])
        )
    sigs: set[tuple[str, float, float, float, float]] = set()
    for item in block.items:
        if isinstance(item, Block):
            sigs |= _all_word_signatures_in_block(item)
    return sigs


def _iter_sibling_groups(blocks: list[Block]) -> Iterator[list[Block]]:
    """Yield every sibling group in the tree: the top level first, then each
    block's own children, recursively."""
    yield blocks
    for block in blocks:
        if block.child_type == BlockChildType.BLOCKS:
            children = [item for item in block.items if isinstance(item, Block)]
            if children:
                yield from _iter_sibling_groups(children)


def find_words_in_multiple_sibling_regions(blocks: list[Block]) -> list[str]:
    """Report a word whose signature is reachable from more than one sibling.

    ``find_duplicated_words`` catches a word the pipeline duplicated anywhere
    on the page, by comparing the whole page's word counts before and after
    reorganize. This checks something narrower and structural: sibling
    regions are disjoint by design, so within any single set of siblings in
    the confirmed block tree, no word signature may be reachable from more
    than one of them. Ancestors are not siblings — a caption block nested
    inside its parent figure block legitimately shares words with it, and
    that nesting is not a violation.
    """
    errors: list[str] = []
    for sibling_group in _iter_sibling_groups(blocks):
        if len(sibling_group) < 2:
            continue
        counts: dict[tuple[str, float, float, float, float], int] = {}
        for block in sibling_group:
            for sig in _all_word_signatures_in_block(block):
                counts[sig] = counts.get(sig, 0) + 1
        for sig, count in counts.items():
            if count <= 1:
                continue
            text, x0, y0, x1, y1 = sig
            errors.append(
                f"word in {count} sibling regions: text={text!r} "
                f"bbox=({x0:.4f},{y0:.4f})-({x1:.4f},{y1:.4f})"
            )
    return errors


class ReorganizeSiblingMembershipError(RuntimeError):
    """Raised in strict mode when a word is reachable from two sibling regions."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__(
            f"reorganize produced {len(errors)} sibling membership violation(s); "
            + f"first: {errors[0] if errors else '(none)'}"
        )
        self.errors: list[str] = errors


def raise_if_words_in_multiple_siblings(
    blocks: list[Block],
    *,
    strict: bool,
) -> list[str]:
    """Return sibling-membership violation errors, raising instead when ``strict``.

    Mirrors ``raise_if_words_duplicated``: loud in CI and tests, recoverable
    in ordinary use so a person still sees the page.
    """
    errors = find_words_in_multiple_sibling_regions(blocks)
    if errors and strict:
        raise ReorganizeSiblingMembershipError(errors)
    return errors
```

- [ ] **Step 4: Run the tests**

Run: `make test-single TEST='tests/ocr/test_sibling_region_membership.py'`
Expected: PASS, all seven tests.

- [ ] **Step 5: Wire it into the reconcile step**

In `reconcile_dropped_words`, immediately after the annotation-preconditions plan's
`duplication_errors = raise_if_words_duplicated(...)` block, add:

```python
    sibling_errors = raise_if_words_in_multiple_siblings(
        final_blocks, strict=reorganize_strict_mode_enabled()
    )
    for message in sibling_errors:
        logger.warning(message)
```

`final_blocks` is the parameter already in scope in `reconcile_dropped_words` — the same candidate
tree `post_words` is gathered from a few lines above, so no new argument is needed.

- [ ] **Step 6: Run the full suite to confirm no existing test regressed**

Run: `make test AI=1`
Expected: PASS. Pay particular attention to `tests/ocr/test_reconcile_dropped_words.py`,
`tests/ocr/test_word_duplication.py`, and `tests/layout/test_layout_aware_reorg.py`, which exercise
the reconcile path and Task 1's refactor together.

- [ ] **Step 7: Run the gate and commit**

```bash
make ci AI=1
git add pdomain_book_tools/ocr/reorganize_page_utils.py tests/ocr/test_sibling_region_membership.py
git commit -m "feat(ocr): assert no word is a member of two sibling regions"
```

---

### Task 3: The proposal-to-region matcher (labeler-spa)

A region carries a stable identifier of its own, and any matching between a proposal and a
confirmed region is done on page and box, never on ordinal — line numbering is not stable across
the band-identification fixes in book-tools, and an earlier analysis in this workspace was
invalidated by matching glyphs on line ordinal across a renumbering. This task adds that matcher:
given a confirmed region and the proposals already scoped to its page, find the one it came from, by
geometric overlap alone.

**Files:**

- Create: `src/pdomain_ocr_labeler_spa/core/regions/matcher.py`
- Test: `pdomain-ocr-labeler-spa/tests/unit/core/regions/test_matcher.py`

**Interfaces:**

- Consumes: `RegionProposal` and `ResolvedRegion` from `pdomain_ocr_labeler_spa.core.regions.models`
  (region-stores-and-resolver plan, Task 1); `iou` from `pdomain_book_contracts.layout.regions`;
  `LayoutRegion` and `RegionType` from `pdomain_book_contracts.layout.types`.
- Produces: `match_proposal_to_region(...)`, with this signature:

```python
def match_proposal_to_region(
    region: ResolvedRegion,
    proposals: Sequence[RegionProposal],
    *,
    iou_threshold: float = 0.5,
) -> RegionProposal | None: ...
```

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/regions/test_matcher.py
"""Unit tests for the geometry-only proposal-to-region matcher."""

from __future__ import annotations

from pdomain_book_contracts.annotation import RegionRole

from pdomain_ocr_labeler_spa.core.regions.models import RegionProposal, ResolvedRegion


def _proposal(proposal_id: str, box: tuple[int, int, int, int], confidence: float) -> RegionProposal:
    return RegionProposal(
        proposal_id=proposal_id,
        run_id="r1",
        page_index=0,
        role=RegionRole.POETRY,
        box=box,
        confidence=confidence,
        evidence={},
    )


def _region(box: tuple[int, int, int, int]) -> ResolvedRegion:
    return ResolvedRegion(
        role=RegionRole.BLOCKQUOTE,
        box=box,
        confirmed=True,
        confidence=None,
        proposal_id=None,
        region_id="reg-1",
    )


def test_the_highest_iou_proposal_wins() -> None:
    from pdomain_ocr_labeler_spa.core.regions.matcher import match_proposal_to_region

    region = _region((0, 0, 100, 100))
    exact_match = _proposal("p-exact", (0, 0, 100, 100), confidence=0.5)
    partial_overlap = _proposal("p-partial", (60, 60, 200, 200), confidence=0.9)

    found = match_proposal_to_region(region, [partial_overlap, exact_match])
    assert found is exact_match


def test_nothing_below_the_threshold_matches() -> None:
    from pdomain_ocr_labeler_spa.core.regions.matcher import match_proposal_to_region

    region = _region((0, 0, 100, 100))
    far_away = _proposal("p1", (200, 200, 300, 300), confidence=0.9)

    assert match_proposal_to_region(region, [far_away]) is None


def test_no_proposals_returns_none() -> None:
    from pdomain_ocr_labeler_spa.core.regions.matcher import match_proposal_to_region

    assert match_proposal_to_region(_region((0, 0, 100, 100)), []) is None


def test_an_iou_tie_goes_to_the_higher_confidence_proposal() -> None:
    from pdomain_ocr_labeler_spa.core.regions.matcher import match_proposal_to_region

    region = _region((0, 0, 100, 100))
    low_confidence = _proposal("p-low", (0, 0, 100, 100), confidence=0.4)
    high_confidence = _proposal("p-high", (0, 0, 100, 100), confidence=0.9)

    found = match_proposal_to_region(region, [low_confidence, high_confidence])
    assert found is high_confidence


def test_an_exact_tie_goes_to_the_lexicographically_smaller_id() -> None:
    from pdomain_ocr_labeler_spa.core.regions.matcher import match_proposal_to_region

    region = _region((0, 0, 100, 100))
    p1 = _proposal("p1", (0, 0, 100, 100), confidence=0.7)
    p2 = _proposal("p2", (0, 0, 100, 100), confidence=0.7)

    assert match_proposal_to_region(region, [p2, p1]) is p1
    assert match_proposal_to_region(region, [p1, p2]) is p1


def test_matching_never_depends_on_list_order() -> None:
    from pdomain_ocr_labeler_spa.core.regions.matcher import match_proposal_to_region

    region = _region((0, 0, 100, 100))
    best = _proposal("p-best", (0, 0, 100, 100), confidence=0.6)
    worse = _proposal("p-worse", (10, 10, 90, 90), confidence=0.6)

    assert match_proposal_to_region(region, [best, worse]) is best
    assert match_proposal_to_region(region, [worse, best]) is best
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/regions/test_matcher.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named '...core.regions.matcher'`

- [ ] **Step 3: Write the implementation**

Create `src/pdomain_ocr_labeler_spa/core/regions/matcher.py`:

```python
"""The proposal-to-region matcher.

A region is identified by its geometry, never by its position in a list or a
line/word ordinal — line numbering is not stable across the
band-identification fixes in book-tools, and an earlier analysis in this
workspace was invalidated by matching glyphs on line ordinal across a
renumbering. So matching a confirmed region back to the proposal it came
from is done on page and box, the same identity everything else in this
design uses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pdomain_book_contracts.layout.regions import iou
from pdomain_book_contracts.layout.types import LayoutRegion, RegionType

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pdomain_ocr_labeler_spa.core.regions.models import RegionProposal, ResolvedRegion


def _as_layout_region(box: tuple[int, int, int, int]) -> LayoutRegion:
    """Wrap a plain box tuple so ``iou`` — built for ``LayoutRegion`` — can be
    reused instead of reimplementing intersection-over-union here.

    ``type`` is a placeholder; ``iou`` reads only the geometry fields.
    """
    left, top, right, bottom = box
    return LayoutRegion(type=RegionType.text, L=left, T=top, R=right, B=bottom, confidence=1.0)


def match_proposal_to_region(
    region: ResolvedRegion,
    proposals: Sequence[RegionProposal],
    *,
    iou_threshold: float = 0.5,
) -> RegionProposal | None:
    """Find which proposal, if any, ``region`` came from.

    ``proposals`` is assumed already scoped to ``region``'s page by the
    caller, the same way ``RegionProposalLog.proposals_for_page`` scopes
    them — this function never sees or needs a page index, and it never
    looks at where a proposal sits in the sequence. Matching is geometry
    only: the proposal with the highest IoU against ``region``'s box wins,
    provided that IoU clears ``iou_threshold``. A tie goes to the
    higher-confidence proposal, then to the lexicographically smaller
    ``proposal_id``, so the result never depends on iteration order.
    """
    region_shape = _as_layout_region(region.box)
    best: RegionProposal | None = None
    best_key: tuple[float, float] = (-1.0, -1.0)
    for proposal in proposals:
        score = iou(region_shape, _as_layout_region(proposal.box))
        if score < iou_threshold:
            continue
        key = (score, proposal.confidence)
        if (
            best is None
            or key > best_key
            or (key == best_key and proposal.proposal_id < best.proposal_id)
        ):
            best, best_key = proposal, key
    return best
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/core/regions/test_matcher.py -v`
Expected: PASS, all six tests.

- [ ] **Step 5: Run the fast suite and the gate**

Run: `make AI=1 test`
Expected: PASS with no regression in the existing suite.

Run: `make AI=1 ci`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/core/regions/matcher.py tests/unit/core/regions/test_matcher.py
git commit -m "feat(regions): match a confirmed region back to its proposal by IoU"
```

---

## What this plan does not do

- It does not add the route that lets a person set a region's explicit word membership, or any
  storage for that decision. That is the fourth (routes) plan, building on the region-stores-and-
  resolver plan this plan's Task 3 already depends on.
- It does not resolve an ambiguous sibling-overlap proposal automatically. `propose_word_regions`
  marks the ragged-notch case `ambiguous`; nothing in this plan picks a winner for it. Only ancestry
  in a confirmed block tree, or a person, can.
- It does not change `drop_layout_regions`, `bubble_block_roles_from_layout`, or
  `drop_figure_internal_words` to read `WordRegionProposal.ambiguous`. They keep reading
  `word.word_labels`, which Task 1 leaves byte-for-byte the same.
- It does not batch-match many regions against many proposals in one call. Task 3 is the single-
  region matcher the design describes; a caller matching a whole page's regions calls it once per
  region.
- It does not filter a matched proposal by an existing `RegionDecision` (for example, skipping one
  already rejected). A caller that needs that composes `match_proposal_to_region` with the decision
  log itself.
- It does not touch `PP_DOCLAYOUT_TO_PGDP` or `_REGION_TO_BLOCK_ROLE`. The folio/page-number mapping
  fix is the annotation-preconditions plan's Task 2, unrelated to membership or matching.

## Related

- [Annotation provenance and
  persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md) — the design,
  especially "Reading order follows explicit membership, not geometry".
- [Region stores and resolver](2026-09-08-region-stores-and-resolver.md) — defines `RegionProposal`
  and `ResolvedRegion`, which Task 3 consumes.
- [Annotation preconditions in book-tools and
  measure](2026-09-08-annotation-preconditions-in-book-tools-and-measure.md) — defines
  `find_duplicated_words`, which Task 2 depends on and does not duplicate.
- [Annotation vocabularies in
  book-contracts](2026-09-08-annotation-vocabularies-in-book-contracts.md) — defines `RegionRole`,
  used by Task 3's tests.
- [Labeling track roadmap](2026-09-07-labeling-track-roadmap.md) — the seven slices this plan's three
  tasks sit inside.
