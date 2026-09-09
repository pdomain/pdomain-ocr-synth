# Page Kind, End to End Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take `PageKind` from a bare enum to a confirmed answer: a typed field on `Page`, a
book-scoped classifier proposal with a real confidence, a per-page reviewed marker, and the job
and routes that connect them.

**Architecture:** Three repos, one pass each, in dependency order. `pdomain-book-tools` gets a
typed `page_kind` field on `Page` that round-trips — this is the only place a page's *confirmed*
kind is ever stored, and only a human action ever writes it. `pdomain-pgdp-measure` turns its
existing per-book classifier's raw pixel residual into a bounded, per-class confidence, using the
group spread `first_band_spread_px` supplies. `pdomain-ocr-labeler-spa` adds the book-scoped job
that reads every page's image, classifies the book, and writes proposals to a new append-only
journal; a confirm route writes the human's answer onto `Page.page_kind` and records a lightweight
reviewed marker — no decision log, because a page has one kind and the human's answer replaces the
machine's whole.

**Tech Stack:** Python, frozen dataclasses, `StrEnum`, JSONL journals with an OS append lock,
FastAPI, pytest, ruff, basedpyright.

**Spec:** [Annotation provenance and
persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md), sections "Page kind
is classified per book, and it runs before regions", "Page kind needs a marker, not a decision
log", and "Three page vocabularies already exist, and they are different axes".

## Agent Index

- **Kind:** plan
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-08
- **Last verified:** 2026-09-08
- **Provenance:** authored 2026-09-08 from the spec above and direct inspection of
  `pdomain-book-tools/pdomain_book_tools/ocr/page.py` and `tests/ocr/test_page_review.py` /
  `test_page_pydantic_schema.py`; `pdomain-pgdp-measure/src/pdomain_pgdp_measure/page_templates.py`,
  `profiling.py`, `profile_models.py`, and `tests/test_pgdp_page_templates.py` /
  `test_pgdp_profile_models.py`; `pdomain-ocr-labeler-spa/src/pdomain_ocr_labeler_spa/core/jobs/runner.py`,
  `core/jobs/handlers/save_project.py` and `auto_rotate_all.py`, `core/project_state.py`,
  `core/page_state.py`, `core/models.py`, `core/persistence/book_labeling_manifest.py`,
  `api/pages.py`, `api/words.py`, `api/projects.py`, its `pyproject.toml`, and
  `tests/unit/api/test_rematch_gt.py` / `test_selection_endpoint.py`; and
  `pdomain-book-contracts/pdomain_book_contracts/typography/book_manifest.py`,
  `pdomain-ops/pdomain_ops/pages/records.py`, and
  `pdomain-prep-for-pgdp/src/pdomain_prep_for_pgdp/core/pipeline/project_stages.py`
- **Disposition:** Active. Closes the gap the annotation-vocabularies plan names explicitly: "It
  defines `PageKind` and nothing consumes it."
- **Read when:** implementing the `Page.page_kind` field, the page-kind confidence normalization,
  the book-scoped `propose_page_kinds` job, or the page-kind confirm route.
- **Search terms:** PageKind, PageClass, PageType, page_class_confidence, first_band_spread_px,
  template_residual_px, PageKindProposal, PageKindProposalRun, PageKindReviewedStore,
  propose_page_kinds, page blob invariant, StageReviewStore.

## Global Constraints

- **Landing order across repos.** This plan depends on two companion plans having shipped first:
  [Annotation vocabularies in
  book-contracts](2026-09-08-annotation-vocabularies-in-book-contracts.md) Task 3 (`PageKind` in
  `pdomain_book_contracts.annotation`), and [Annotation preconditions in book-tools and
  measure](2026-09-08-annotation-preconditions-in-book-tools-and-measure.md) Task 3
  (`PageTemplate.first_band_spread_px`). Task 2 of this plan cannot start before that lands. Task 1
  of this plan (book-tools) must ship and be released before Task 7 (the labeler's confirm route)
  can bump its pin and round-trip `page_kind` through the event store.
- **The page blob is only ever written by a human action.** `propose_page_kinds` (Task 6) writes
  proposals to its own journal and never calls `save_page_content_to_store` and never sets
  `Page.page_kind`. Only the confirm route (Task 7) does either.
- **Journals are append-only.** Follow `pdomain-ocr-labeler-spa/core/typography_review.py`'s
  `TypographyCorrectionLog`: an OS append lock (`fcntl.flock(fd, fcntl.LOCK_EX)`), `os.fsync`
  before `append` returns, and no record ever rewritten in place. This is the same discipline the
  region-stores plan's `RegionProposalLog` and `RegionDecisionLog` already use.
- **Naming.** The enum is `PageKind`, never `PageType`. Do not merge it with `PageClass` in
  `pdomain-pgdp-measure` (a measured signal) or `PageType` in `pdomain-prep-for-pgdp` (a packaging
  decision). See the spec's "Three page vocabularies already exist, and they are different axes".
- **`pdomain-pgdp-measure` adds zero dependencies.** Its runtime dependency set is exactly
  `pydantic`, `pillow`, `numpy` on purpose — "Adding a fourth fails the extraction plan" per its own
  `pyproject.toml`. Task 2 stays inside `page_templates.py`, `profiling.py`, and
  `profile_models.py`, and never imports `pdomain-book-contracts`. The `PageClass` → `PageKind`
  mapping lives in the labeler (Task 6), the one repo that already depends on both.
- **Name collision to avoid.** `pdomain_pgdp_measure.page_templates.PageClassification` (page
  class + residual + confidence) and `pdomain_pgdp_measure.alignment_review.PageClassification`
  (category + exclusions) are two unrelated classes with the same name in different modules. Always
  import from `page_templates`.
- **book-tools:** Python `>=3.11,<3.14`. `filterwarnings = ["error"]`. `make setup AI=1`,
  `make test AI=1`, `make test-single TEST='tests/...::test_name'`, `make ci AI=1`.
- **pgdp-measure:** Python `>=3.13,<3.14`. No Makefile — `uv run pytest`, `uv run ruff check .`,
  `uv run ruff format --check .`, `uv run basedpyright`. `pythonpath = ["src"]`. Warnings are
  errors.
- **labeler:** Python `>=3.13,<3.14`. `make test`, `make AI=1 ci`. `asyncio_mode = "auto"` — async
  test functions need no `@pytest.mark.asyncio`.

---

## File Structure

| repo | file | responsibility |
| --- | --- | --- |
| book-tools | `pdomain_book_tools/ocr/page.py` | modified: `Page` gains a typed, round-tripping `page_kind` |
| book-tools | `tests/ocr/test_page_kind.py` | covers the new field: default, round-trip, invalid value, scale |
| book-tools | `tests/ocr/test_page_pydantic_schema.py` | modified: schema-shape test grows `page_kind` |
| pgdp-measure | `src/pdomain_pgdp_measure/page_templates.py` | modified: `PageClassification` gains `confidence` |
| pgdp-measure | `src/pdomain_pgdp_measure/profiling.py` | modified: copies confidence into `PageMeasurement` |
| pgdp-measure | `src/pdomain_pgdp_measure/profile_models.py` | modified: adds `page_class_confidence` |
| pgdp-measure | `schemas/pgdp-profile-v2.schema.json` | modified: documents the new property |
| pgdp-measure | `tests/test_pgdp_page_templates.py` | modified: covers confidence, its bounds, the unknown case |
| pgdp-measure | `tests/test_pgdp_profile_models.py` | modified: covers the round trip and the missing-key default |
| labeler | `src/pdomain_ocr_labeler_spa/core/page_kind/models.py` | `PageKindProposal`, `PageKindProposalRun` |
| labeler | `src/pdomain_ocr_labeler_spa/core/page_kind/proposal_log.py` | append-only proposal-run journal |
| labeler | `src/pdomain_ocr_labeler_spa/core/page_kind/reviewed_store.py` | append-only per-page reviewed markers |
| labeler | `src/pdomain_ocr_labeler_spa/core/jobs/handlers/propose_page_kinds.py` | the book-scoped job |
| labeler | `src/pdomain_ocr_labeler_spa/core/jobs/runner.py` | modified: registers the handler |
| labeler | `src/pdomain_ocr_labeler_spa/api/projects.py` | modified: `POST .../propose-page-kinds` → 202 |
| labeler | `src/pdomain_ocr_labeler_spa/api/pages.py` | modified: `POST .../page-kind` confirms a kind |
| labeler | `pyproject.toml` | modified: adds `pdomain-pgdp-measure`; bumps the book-tools pin |
| labeler | `tests/unit/core/page_kind/test_page_kind_models.py` | model round-trips and validation |
| labeler | `tests/unit/core/page_kind/test_proposal_log.py` | append, read back, latest-per-page lookup |
| labeler | `tests/unit/core/page_kind/test_reviewed_store.py` | append, read back, most-recent-wins |
| labeler | `tests/unit/core/jobs/test_propose_page_kinds_handler.py` | the handler, against injected measurements |
| labeler | `tests/unit/api/test_propose_page_kinds_endpoint.py` | the start-job route |
| labeler | `tests/unit/api/test_page_kind_endpoint.py` | the confirm route |

---

### Task 1: `Page.page_kind` — the confirmed answer's only home

`Page` today carries a free-form `page_labels: list[str] | None` with no allowed-values constant,
plus `review: ReviewMetadata | None`. Confirmed page kind needs its own typed, validated field, the
same way a region role is validated — not another string dropped into `page_labels`.

Five places need the new field, and `Page`'s own pydantic schema hook is the trap: it is a
hand-written `typed_dict_schema` with its own field list, separate from `to_dict`/`from_dict`, and
`tests/ocr/test_page_pydantic_schema.py::test_page_json_schema_shape` asserts an *exact* set of
schema property keys. Miss either one and the field silently doesn't round-trip through
`TypeAdapter`, or the existing test fails for an unrelated reason.

**Files:**

- Modify: `pdomain_book_tools/ocr/page.py`
- Modify: `tests/ocr/test_page_pydantic_schema.py`
- Test: `tests/ocr/test_page_kind.py`

**Interfaces:**

- Consumes: `PageKind` from `pdomain_book_contracts.annotation` (ships in the annotation-vocabularies
  plan's Task 3).
- Produces: `Page.page_kind: PageKind | None`, defaulting to `None` so every stored page keeps
  loading.

- [ ] **Step 1: Write the failing test**

```python
# tests/ocr/test_page_kind.py
"""Tests for Page.page_kind (typed, validated page-kind field)."""

from __future__ import annotations

import pytest

from pdomain_book_contracts.annotation import PageKind
from pdomain_book_tools.ocr.page import Page


def _minimal_page() -> Page:
    """Build a minimal Page suitable for page_kind-field tests."""
    return Page(width=100, height=100, page_index=0, blocks=[])


def test_page_kind_defaults_to_none():
    p = _minimal_page()
    assert p.page_kind is None


def test_page_kind_accepts_a_page_kind_member():
    p = _minimal_page()
    p.page_kind = PageKind.CHAPTER_OPENING
    assert p.page_kind is PageKind.CHAPTER_OPENING


def test_page_to_dict_omits_page_kind_key_when_none():
    p = _minimal_page()
    d = p.to_dict()
    assert "page_kind" not in d


def test_page_to_dict_includes_page_kind_when_set():
    p = _minimal_page()
    p.page_kind = PageKind.TITLE_PAGE
    d = p.to_dict()
    assert d["page_kind"] == "title page"


def test_page_kind_roundtrip():
    p = _minimal_page()
    p.page_kind = PageKind.INDEX
    p2 = Page.from_dict(p.to_dict())
    assert p2.page_kind is PageKind.INDEX


def test_a_stored_page_without_page_kind_still_loads():
    """A page written before this field existed must keep loading."""
    p = _minimal_page()
    d = p.to_dict()
    assert "page_kind" not in d
    p2 = Page.from_dict(d)
    assert p2.page_kind is None


def test_an_invalid_stored_page_kind_raises():
    p = _minimal_page()
    d = p.to_dict()
    d["page_kind"] = "not-a-real-kind"
    with pytest.raises(ValueError, match="not-a-real-kind"):
        Page.from_dict(d)


def test_page_kind_survives_scale():
    p = _minimal_page()
    p.page_kind = PageKind.BODY
    scaled = p.scale(200, 200)
    assert scaled.page_kind is PageKind.BODY
```

- [ ] **Step 2: Run test to verify it fails**

Run: `make test-single TEST='tests/ocr/test_page_kind.py'`
Expected: FAIL with `AttributeError: 'Page' object has no attribute 'page_kind'`.

- [ ] **Step 3: Write the implementation**

In `pdomain_book_tools/ocr/page.py`, add the import, right before the existing
`pdomain_book_tools.geometry.bounding_box` import (book-contracts before book-tools,
alphabetically):

```python
from pdomain_book_contracts.annotation import PageKind

from pdomain_book_tools.geometry.bounding_box import BoundingBox
```

Add the field right after the existing `review` field:

```python
    # Optional human-review metadata (Page-scope). See
    # pdomain_book_tools/ocr/review.py.
    review: ReviewMetadata | None = None

    # What this page is — title page, chapter opening, body, and so on. Only a
    # human action ever sets this (never the propose_page_kinds classifier job);
    # see pdomain-ocr-synth's docs/specs/2026-09-07-region-provenance-and-persistence-design.md
    # "Page kind is classified per book, and it runs before regions".
    page_kind: PageKind | None = None
```

In `to_dict`, right after the existing `review` block:

```python
        if self.review is not None:
            result["review"] = self.review.to_dict()
        if self.page_kind is not None:
            result["page_kind"] = self.page_kind.value
```

In `from_dict`, right after the existing `page_labels` restoration block, before `return cls(...)`:

```python
        # page_kind: restore and validate against PageKind when present. A page
        # written before this field existed has no "page_kind" key and loads
        # with page_kind=None, matching every other optional field here.
        page_kind_raw = data.get("page_kind")
        page_kind: PageKind | None = (
            PageKind(str(page_kind_raw)) if page_kind_raw is not None else None
        )

        return cls(
            blocks=blocks,
            page_id=page_id,
            width=int(cast("str | float | int", data["width"])),
            height=int(cast("str | float | int", data["height"])),
            page_index=int(cast("str | float | int", data["page_index"])),
            bounding_box=bounding_box,
            page_labels=page_labels,
            name=cast("str | None", data.get("name")),
            review=review,
            page_kind=page_kind,
            image_blob_hash=cast("str | None", data.get("image_blob_hash")),
            thumbnail_blob_hash=cast("str | None", data.get("thumbnail_blob_hash")),
            gt_orphans=gt_orphans,
        )
```

In `scale`, add `page_kind=self.page_kind,` to the returned `Page(...)`, and extend the docstring's
field list:

```python
        Fields preserved include ``page_id`` (entity identity), ``page_labels``,
        ``name``, ``review``, and ``page_kind``.
        """
        return Page(
            width=width,
            height=height,
            page_index=self.page_index,
            blocks=[item.scale(width, height) for item in self.items],
            bounding_box=self.bounding_box.scale(width, height)
            if self.bounding_box
            else None,
            page_id=self.page_id,
            page_labels=self.page_labels,
            name=self.name,
            review=self.review,
            page_kind=self.page_kind,
            image_blob_hash=self.image_blob_hash,
            thumbnail_blob_hash=self.thumbnail_blob_hash,
            gt_orphans=self.gt_orphans,
        )
```

In `__get_pydantic_core_schema__`, add one entry right after the existing `"review"` field, reusing
`NULLABLE_STR_SCHEMA` the same way `"name"` and `"page_id"` already do:

```python
                    "review": core_schema.typed_dict_field(
                        core_schema.nullable_schema(review_schema),
                        required=False,
                    ),
                    "page_kind": core_schema.typed_dict_field(
                        NULLABLE_STR_SCHEMA,
                        required=False,
                    ),
                    "image_blob_hash": core_schema.typed_dict_field(
```

- [ ] **Step 4: Update the schema-shape test — it asserts an exact key set**

`tests/ocr/test_page_pydantic_schema.py::test_page_json_schema_shape` asserts
`set(props.keys()) == expected_keys`. Add `"page_kind"` to that set:

```python
    expected_keys = {
        "type",
        "page_id",
        "width",
        "height",
        "page_index",
        "bounding_box",
        "items",
        "page_labels",
        "name",
        "review",
        "page_kind",
        "image_blob_hash",
        "thumbnail_blob_hash",
        "gt_orphans",
    }
```

- [ ] **Step 5: Run the tests**

Run: `make test-single TEST='tests/ocr/test_page_kind.py'`
Expected: PASS, all eight tests.

Run: `make test-single TEST='tests/ocr/test_page_pydantic_schema.py'`
Expected: PASS.

- [ ] **Step 6: Run the full suite and the gate**

Run: `make test AI=1`
Expected: PASS with no regression.

Run: `make ci AI=1`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add pdomain_book_tools/ocr/page.py tests/ocr/test_page_kind.py tests/ocr/test_page_pydantic_schema.py
git commit -m "feat(ocr): add a typed, validated page_kind field to Page"
```

---

### Task 2: Turn `template_residual_px` into a per-class confidence

`template_residual_px` is a raw pixel distance: unbounded, and lower is better — the opposite
polarity of every other confidence in the suite. `PageTemplate.first_band_spread_px` (added by the
annotation-preconditions plan's Task 3) supplies the missing scale: a normal page's residual is
bounded by the book's head window (as small as 8 pixels), while a chapter opening's is measured
against a template fitted from pages that sank by widely differing amounts, so each template must
be scored against its own spread.

`PageClassification` already carries `template_residual_px` and is computed inside `_classify_page`,
which already has the winning `template` in scope at both points it returns a non-`unknown`
classification. Only those two return statements change; every `unknown` return keeps its existing
four positional arguments unchanged, because the new field defaults to `None`.

**Files:**

- Modify: `src/pdomain_pgdp_measure/page_templates.py`
- Modify: `src/pdomain_pgdp_measure/profiling.py`
- Modify: `src/pdomain_pgdp_measure/profile_models.py`
- Modify: `schemas/pgdp-profile-v2.schema.json`
- Test: `tests/test_pgdp_page_templates.py`
- Test: `tests/test_pgdp_profile_models.py`

**Interfaces:**

- Consumes: `PageTemplate.first_band_spread_px` from the annotation-preconditions plan's Task 3.
- Produces: `PageClassification.confidence: float | None` and
  `PageMeasurement.page_class_confidence: float | None`, both round-tripping through the wire
  contract.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_pgdp_page_templates.py`, reusing the file's existing `_steady_book` / `_page`
helpers:

```python
def test_normal_pages_score_full_confidence_on_an_exact_match() -> None:
    pages = _steady_book()
    templates = fit_book_templates(pages)
    classified = {item.page_name: item for item in classify_pages(pages, templates)}
    assert classified["p001.png"].confidence == 1.0


def test_an_unknown_page_has_no_confidence() -> None:
    trough = _page("p021.png", first_band_top=151)
    pages = (*_steady_book(), trough)
    templates = fit_book_templates(pages)
    classified = {item.page_name: item for item in classify_pages(pages, templates)}
    assert classified["p021.png"].page_class == "unknown"
    assert classified["p021.png"].confidence is None


def test_confidence_is_bounded_between_zero_and_one_for_a_chapter_opening() -> None:
    pages = (*_steady_book(), _page("p021.png", first_band_top=367, bands=20))
    templates = fit_book_templates(pages)
    classified = {item.page_name: item for item in classify_pages(pages, templates)}
    opening = classified["p021.png"]
    assert opening.page_class == "chapter_opening"
    assert opening.confidence is not None
    assert 0.0 <= opening.confidence <= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pgdp_page_templates.py -v`
Expected: FAIL with `AttributeError: 'PageClassification' object has no attribute 'confidence'`.

- [ ] **Step 3: Add the field, the helper, and wire the two informative branches**

In `src/pdomain_pgdp_measure/page_templates.py`, add one field to `PageClassification`, after
`furniture_band_ordinals`:

```python
@dataclass(frozen=True, slots=True)
class PageClassification:
    """One page's class and how far it sat from its template."""

    page_name: str
    page_class: PageClass
    template_residual_px: int | None
    furniture_band_ordinals: tuple[int, ...]
    confidence: float | None = None
```

Add the confidence helper, near the other module-level helpers:

```python
def _confidence_from_residual(residual_px: int, template: PageTemplate) -> float:
    """Invert and scale a template residual into a 0..1 confidence.

    ``template_residual_px`` is a raw pixel distance: unbounded, and lower is
    better, the opposite polarity of every other confidence in the suite. The
    scale is the spread of the template's own fitted group
    (``first_band_spread_px``), floored at ``_HEAD_WINDOW_MINIMUM_PX`` so a
    single-page group — whose spread is 0 — never divides by zero and never
    collapses every nonzero residual straight to 0. A normal page's spread is
    bounded by the book's head window; a chapter opening's is measured against
    pages that sank by widely differing amounts, so each template scores
    against its own spread rather than one shared constant.
    """

    scale_px = max(template.first_band_spread_px, _HEAD_WINDOW_MINIMUM_PX)
    return max(0.0, 1.0 - (residual_px / scale_px))
```

In `_classify_page`, compute the residual once and pass confidence at both informative return
sites. The normal-match branch:

```python
        # The running head is printed but deleted from F2, so the aligner must not
        # match a source line to it. Nothing is printed above the head, so every
        # band down to and including it is furniture.
        residual = int(abs(head_top - template.first_band_top_px))
        return PageClassification(
            geometry.page_name,
            template.page_class,
            residual,
            tuple(range(head_ordinal + 1)),
            _confidence_from_residual(residual, template),
        )
```

The chapter-opening branch:

```python
    if offset >= _CHAPTER_SINK_MINIMUM_PX and "chapter_opening" in by_class:
        template = by_class["chapter_opening"]
        residual = int(abs(head_top - template.first_band_top_px))
        return PageClassification(
            geometry.page_name,
            "chapter_opening",
            residual,
            (),
            _confidence_from_residual(residual, template),
        )
```

Every other `PageClassification(...)` call in this module already stays `"unknown"` with a `None`
residual and needs no change — `confidence` defaults to `None` there too.

- [ ] **Step 4: Run the new tests**

Run: `uv run pytest tests/test_pgdp_page_templates.py -v`
Expected: PASS, the three new tests plus the existing ones in this file (the confidence field is
additive; no existing test does a full-object equality against `PageClassification`).

- [ ] **Step 5: Carry the confidence into `PageMeasurement`**

In `src/pdomain_pgdp_measure/profiling.py`, `_with_page_class` already copies the classification
onto the measurement. Add one line:

```python
def _with_page_class(
    measurement: PageMeasurement, classification: PageClassification | None
) -> PageMeasurement:
    if classification is None:
        return measurement
    return replace(
        measurement,
        page_class=classification.page_class,
        template_residual_px=classification.template_residual_px,
        furniture_band_ordinals=classification.furniture_band_ordinals,
        page_class_confidence=classification.confidence,
    )
```

In `src/pdomain_pgdp_measure/profile_models.py`, add `StrictFloat` to the existing `pydantic`
import:

```python
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StrictFloat,
    StrictInt,
    StrictStr,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)
```

Add the field to `PageMeasurement`, right after `furniture_band_ordinals`:

```python
    page_class_confidence: float | None = None
```

Add it to `PageMeasurement.to_dict`, right after `"furniture_band_ordinals"` (this dict is emitted
unconditionally, matching the sibling fields — never gated behind an `if`):

```python
                "page_class_confidence": self.page_class_confidence,
```

`PageMeasurementWire` is a *separate* pydantic model with its own hardcoded field list and its own
`to_domain` — the exact trap that dropped `first_band_spread_px` in the preconditions plan if its
Task 3 were skipped there. Add the field right after `furniture_band_ordinals`:

```python
    page_class_confidence: StrictFloat | None = None
```

And to `to_domain`, right after `furniture_band_ordinals=self.furniture_band_ordinals,`:

```python
            page_class_confidence=self.page_class_confidence,
```

- [ ] **Step 6: Write the round-trip test**

Add to `tests/test_pgdp_profile_models.py`, reusing the existing `_page`/`_report` helpers:

```python
def test_page_class_confidence_survives_a_profile_round_trip() -> None:
    page = replace(
        _page(), page_class="chapter_opening", template_residual_px=12, page_class_confidence=0.4
    )
    project = ProjectProfile(
        project_id="projectID1", title=None, author=None, genre=None, pages=(page,),
        pooled_estimates=(),
    )
    report = ProfileReport(
        source_ranking={"algorithm_version": "pgdp-rank/v1", "sha256": "b" * 64},
        methods={},
        projects=(project,),
    )
    restored = ProfileReport.from_dict(report.to_dict())
    assert restored.projects[0].pages[0].page_class_confidence == 0.4


def test_a_stored_page_without_page_class_confidence_still_validates() -> None:
    payload = _report().to_dict()
    del payload["projects"][0]["pages"][0]["page_class_confidence"]
    restored = ProfileReportWire.model_validate(payload).to_domain()
    assert restored.projects[0].pages[0].page_class_confidence is None
```

- [ ] **Step 7: Run the tests**

Run: `uv run pytest tests/test_pgdp_profile_models.py -v`
Expected: PASS, both new tests plus the existing ones in this file.

- [ ] **Step 8: Regenerate the profile schema**

```bash
uv run python -c "
from pathlib import Path
from pdomain_pgdp_measure.profile_models import profile_schema_json
Path('schemas/pgdp-profile-v2.schema.json').write_text(profile_schema_json())
"
```

Run: `grep -n "page_class_confidence" schemas/pgdp-profile-v2.schema.json`
Expected: at least one hit.

- [ ] **Step 9: Run the full suite, lint, and typecheck**

Run: `uv run pytest`
Expected: PASS. Warnings are errors, so a new deprecation surfaces as a failure.

Run: `uv run ruff format --check .`
Run: `uv run ruff check .`
Expected: PASS.

Run: `uv run basedpyright`
Expected: **not** a clean pass, and it never was on this repo. Measured at master `a3910dc`
before this task: 1442 errors and 948 warnings, every one of them inside `tests/`; scoped to
`src/` it is genuinely 0 errors. 1037 of those errors sit in `tests/test_pgdp_profile_models.py`
alone, where `to_dict()` returns `dict[str, JsonValue]` and basedpyright cannot narrow through
repeated subscripting — the file relies on that un-narrowable 4-level chain at dozens of sites
already. Step 6's `del payload["projects"][0]["pages"][0]["page_class_confidence"]` is the same
pattern and adds 23 more.

The bar to hold is therefore: **`src/` stays at 0 errors, and no new warnings appear on the
three files this task touches.** Do not silence the new test line with a `cast()` or a
`# type: ignore` — annotating one site while ~50 identical pre-existing ones stay bare would
contradict the file's own convention and hide the real problem, which is that this repo's test
tree has never been typed to the gate's standard. That cleanup is its own task.

- [ ] **Step 10: Commit**

```bash
git add src/pdomain_pgdp_measure tests/test_pgdp_page_templates.py tests/test_pgdp_profile_models.py \
  schemas/pgdp-profile-v2.schema.json
git commit -m "feat(templates): turn template_residual_px into a per-class confidence"
```

---

### Task 3: Page-kind proposal and run records (labeler)

Mirrors `core/regions/models.py`'s `RegionProposal` / `ProposalRun`, minus what page kind doesn't
need: no `page_kind_decision_ref` (nothing upstream feeds page kind — it is the base case regions
are conditioned on), and confidence may be `None` (the classifier's refusal, not a range violation).

**Files:**

- Create: `src/pdomain_ocr_labeler_spa/core/page_kind/__init__.py`
- Create: `src/pdomain_ocr_labeler_spa/core/page_kind/models.py`
- Test: `tests/unit/core/page_kind/test_page_kind_models.py`

**Interfaces:**

- Consumes: `PageKind` from `pdomain_book_contracts.annotation`.
- Produces: `PageKindProposal`, `PageKindProposalRun`, each with `to_dict` and `from_dict`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/page_kind/test_page_kind_models.py
"""Unit tests for the page-kind proposal and run records."""

from __future__ import annotations

import pytest


def test_a_proposal_round_trips() -> None:
    from pdomain_book_contracts.annotation import PageKind

    from pdomain_ocr_labeler_spa.core.page_kind.models import PageKindProposal

    proposal = PageKindProposal(
        proposal_id="p1",
        run_id="r1",
        page_index=3,
        kind=PageKind.CHAPTER_OPENING,
        confidence=0.82,
        evidence={"page_class": "chapter_opening", "template_residual_px": 4},
    )
    restored = PageKindProposal.from_dict(proposal.to_dict())
    assert restored == proposal
    assert restored.kind is PageKind.CHAPTER_OPENING
    assert restored.evidence["template_residual_px"] == 4


def test_a_proposal_allows_no_confidence_for_the_classifier_s_refusal() -> None:
    from pdomain_book_contracts.annotation import PageKind

    from pdomain_ocr_labeler_spa.core.page_kind.models import PageKindProposal

    proposal = PageKindProposal(
        proposal_id="p1", run_id="r1", page_index=0, kind=PageKind.UNKNOWN,
        confidence=None, evidence={},
    )
    restored = PageKindProposal.from_dict(proposal.to_dict())
    assert restored.confidence is None


def test_a_proposal_rejects_a_confidence_outside_zero_to_one() -> None:
    from pdomain_book_contracts.annotation import PageKind

    from pdomain_ocr_labeler_spa.core.page_kind.models import PageKindProposal

    with pytest.raises(ValueError, match="confidence"):
        PageKindProposal(
            proposal_id="p1", run_id="r1", page_index=0, kind=PageKind.BODY,
            confidence=1.4, evidence={},
        )


def test_a_run_round_trips() -> None:
    from pdomain_ocr_labeler_spa.core.page_kind.models import PageKindProposalRun

    run = PageKindProposalRun(
        run_id="r1",
        model_id="pgdp-measure/page-templates",
        model_version="first-band-templates/v3",
        created_at="2026-09-08T10:00:00+00:00",
        page_count=42,
    )
    restored = PageKindProposalRun.from_dict(run.to_dict())
    assert restored == run
```

- [ ] **Step 2: Run test to verify it fails**

Run: `make test-single TEST='tests/unit/core/page_kind/test_page_kind_models.py'` — this repo has
no `test-single` target; run: `uv run pytest tests/unit/core/page_kind/test_page_kind_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pdomain_ocr_labeler_spa.core.page_kind'`

- [ ] **Step 3: Write the implementation**

Create `src/pdomain_ocr_labeler_spa/core/page_kind/__init__.py` as an empty module docstring file,
then `src/pdomain_ocr_labeler_spa/core/page_kind/models.py`:

```python
"""Records that keep a book-scoped page-kind classifier's claims beside a
person's confirmed answer.

Page kind is classified per book, proposed here, and confirmed by a human
directly onto ``Page.page_kind``. Unlike regions, page kind needs no decision
log: a page has one kind, so the human's answer replaces the machine's whole.
See pdomain-ocr-synth's docs/specs/2026-09-07-region-provenance-and-persistence-design.md "Page
kind needs a marker, not a decision log".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pdomain_book_contracts.annotation import PageKind


@dataclass(frozen=True)
class PageKindProposalRun:
    """One book-scoped pass of the page-kind classifier."""

    run_id: str
    model_id: str
    model_version: str
    created_at: str
    page_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "created_at": self.created_at,
            "page_count": self.page_count,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PageKindProposalRun:
        return cls(
            run_id=str(d["run_id"]),
            model_id=str(d["model_id"]),
            model_version=str(d["model_version"]),
            created_at=str(d["created_at"]),
            page_count=int(d["page_count"]),
        )


@dataclass(frozen=True)
class PageKindProposal:
    """One page's proposed kind. Never edited after it is written.

    ``confidence`` is ``None`` for the classifier's own refusal (``kind`` is
    then ``PageKind.UNKNOWN``) — a missing confidence, not a zero one.
    """

    proposal_id: str
    run_id: str
    page_index: int
    kind: PageKind
    confidence: float | None
    evidence: dict[str, Any]

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence {self.confidence} is outside 0.0 to 1.0")

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "run_id": self.run_id,
            "page_index": self.page_index,
            "kind": self.kind.value,
            "confidence": self.confidence,
            "evidence": dict(self.evidence),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PageKindProposal:
        confidence = d.get("confidence")
        return cls(
            proposal_id=str(d["proposal_id"]),
            run_id=str(d["run_id"]),
            page_index=int(d["page_index"]),
            kind=PageKind(str(d["kind"])),
            confidence=float(confidence) if confidence is not None else None,
            evidence=dict(d.get("evidence") or {}),
        )
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/core/page_kind/test_page_kind_models.py -v`
Expected: PASS, all four tests.

- [ ] **Step 5: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/core/page_kind tests/unit/core/page_kind/test_page_kind_models.py
git commit -m "feat(page-kind): add proposal and run records"
```

---

### Task 4: The proposal journal (labeler)

Mirrors `core/regions/proposal_log.py`'s `RegionProposalLog` exactly, at its own path.

**Files:**

- Create: `src/pdomain_ocr_labeler_spa/core/page_kind/proposal_log.py`
- Test: `tests/unit/core/page_kind/test_proposal_log.py`

**Interfaces:**

- Consumes: `PageKindProposal` and `PageKindProposalRun` from Task 3.
- Produces: `PageKindProposalLog(project_root: Path)` with `append_run`, `append_proposals`,
  `runs() -> list[PageKindProposalRun]`, `proposals_for_run(run_id: str) -> list[PageKindProposal]`,
  and `latest_proposal_for_page(page_index: int) -> PageKindProposal | None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/page_kind/test_proposal_log.py
"""Unit tests for the append-only page-kind proposal journal."""

from __future__ import annotations

from pathlib import Path

from pdomain_book_contracts.annotation import PageKind

from pdomain_ocr_labeler_spa.core.page_kind.models import PageKindProposal, PageKindProposalRun


def _run(run_id: str = "r1", page_count: int = 2) -> PageKindProposalRun:
    return PageKindProposalRun(
        run_id=run_id, model_id="pgdp-measure/page-templates",
        model_version="first-band-templates/v3", created_at="2026-09-08T10:00:00+00:00",
        page_count=page_count,
    )


def _proposal(proposal_id: str, run_id: str = "r1", page_index: int = 0) -> PageKindProposal:
    return PageKindProposal(
        proposal_id=proposal_id, run_id=run_id, page_index=page_index,
        kind=PageKind.BODY, confidence=0.9, evidence={},
    )


def test_a_run_and_its_proposals_read_back(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.page_kind.proposal_log import PageKindProposalLog

    log = PageKindProposalLog(tmp_path)
    log.append_run(_run())
    log.append_proposals([_proposal("p1", page_index=0), _proposal("p2", page_index=1)])

    assert [r.run_id for r in log.runs()] == ["r1"]
    assert sorted(p.proposal_id for p in log.proposals_for_run("r1")) == ["p1", "p2"]


def test_a_fresh_log_is_empty_and_does_not_raise(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.page_kind.proposal_log import PageKindProposalLog

    log = PageKindProposalLog(tmp_path)
    assert log.runs() == []
    assert log.latest_proposal_for_page(0) is None


def test_latest_proposal_for_page_wins_across_runs(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.page_kind.proposal_log import PageKindProposalLog

    log = PageKindProposalLog(tmp_path)
    log.append_run(_run("r1"))
    log.append_proposals([_proposal("p1", run_id="r1", page_index=0)])
    log.append_run(_run("r2"))
    log.append_proposals([_proposal("p2", run_id="r2", page_index=0)])

    latest = log.latest_proposal_for_page(0)
    assert latest is not None
    assert latest.proposal_id == "p2"
    # Both runs survive — this is what makes one detector scoreable against another.
    assert [r.run_id for r in log.runs()] == ["r1", "r2"]


def test_appending_never_rewrites_an_existing_record(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.page_kind.proposal_log import PageKindProposalLog

    log = PageKindProposalLog(tmp_path)
    log.append_run(_run())
    log.append_proposals([_proposal("p1")])
    first = (tmp_path / ".pd-pages" / "page-kind-proposals.jsonl").read_bytes()

    log.append_proposals([_proposal("p2", page_index=1)])
    second = (tmp_path / ".pd-pages" / "page-kind-proposals.jsonl").read_bytes()

    assert second.startswith(first)


def test_a_malformed_line_is_skipped_rather_than_failing_the_read(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.page_kind.proposal_log import PageKindProposalLog

    log = PageKindProposalLog(tmp_path)
    log.append_run(_run())
    log.append_proposals([_proposal("p1")])
    path = tmp_path / ".pd-pages" / "page-kind-proposals.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{not json\n")

    assert log.latest_proposal_for_page(0) is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/page_kind/test_proposal_log.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named '...core.page_kind.proposal_log'`

- [ ] **Step 3: Write the implementation**

Create `src/pdomain_ocr_labeler_spa/core/page_kind/proposal_log.py`:

```python
"""Append-only journal of page-kind proposals and the runs that produced them.

Mirrors ``core/regions/proposal_log.py``'s ``RegionProposalLog``: one run
record per book-scoped pass, one record per proposed page kind, and the same
discipline as ``TypographyCorrectionLog`` — an OS append lock, fsync before
``append`` returns, and no record ever rewritten.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any, ClassVar

from pdomain_ocr_labeler_spa.core.page_kind.models import PageKindProposal, PageKindProposalRun

log = logging.getLogger(__name__)


class PageKindProposalLog:
    """Project-local JSONL journal of immutable page-kind proposals."""

    _RELATIVE_PATH: ClassVar[Path] = Path(".pd-pages") / "page-kind-proposals.jsonl"

    def __init__(self, project_root: Path) -> None:
        self._path = Path(project_root) / self._RELATIVE_PATH

    @property
    def path(self) -> Path:
        return self._path

    def _append(self, records: Sequence[dict[str, Any]]) -> None:
        if not records:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = "".join(json.dumps(record, sort_keys=True) + "\n" for record in records).encode(
            "utf-8"
        )
        fd = os.open(self._path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            os.write(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)

    def append_run(self, run: PageKindProposalRun) -> None:
        """Record one proposal run before its proposals are written."""
        self._append([{"kind": "run", "record": run.to_dict()}])

    def append_proposals(self, proposals: Sequence[PageKindProposal]) -> None:
        """Append proposals. Existing records are never touched."""
        self._append([{"kind": "proposal", "record": p.to_dict()} for p in proposals])

    def _read(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self._path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    loaded = json.loads(stripped)
                except json.JSONDecodeError:
                    log.warning(
                        "page-kind-proposals.jsonl: skipping malformed line %d", line_number
                    )
                    continue
                if isinstance(loaded, dict):
                    records.append(loaded)
        return records

    def runs(self) -> list[PageKindProposalRun]:
        """Every run recorded, in the order they were written."""
        return [
            PageKindProposalRun.from_dict(entry["record"])
            for entry in self._read()
            if entry.get("kind") == "run"
        ]

    def proposals_for_run(self, run_id: str) -> list[PageKindProposal]:
        """Every proposal written by one run."""
        return [
            PageKindProposal.from_dict(entry["record"])
            for entry in self._read()
            if entry.get("kind") == "proposal" and entry["record"].get("run_id") == run_id
        ]

    def latest_proposal_for_page(self, page_index: int) -> PageKindProposal | None:
        """The most recent proposal for one page, across every run.

        The confirm route diffs the human's answer against this to tell an
        acceptance from a change — no decision log needed at this level.
        """
        latest: PageKindProposal | None = None
        for entry in self._read():
            if entry.get("kind") != "proposal":
                continue
            proposal = PageKindProposal.from_dict(entry["record"])
            if proposal.page_index == page_index:
                latest = proposal
        return latest
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/core/page_kind/test_proposal_log.py -v`
Expected: PASS, all five tests.

- [ ] **Step 5: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/core/page_kind/proposal_log.py \
  tests/unit/core/page_kind/test_proposal_log.py
git commit -m "feat(page-kind): add the append-only proposal journal"
```

---

### Task 5: The reviewed-marker store (labeler)

The design's rule for page kind: a page has one kind, so the human's answer replaces the machine's
whole outright. Diffing the confirmed value against `latest_proposal_for_page` (Task 4) already
tells you accepted-or-changed. This store answers the other half — whether anyone has looked at
all — the same shape `pdomain-prep-for-pgdp`'s `StageReviewStore` records
(`confirmed_at`/`actor_id`/`note`), but keyed per page rather than per project-wide stage, and as a
project-local JSONL journal rather than SQLite, matching this repo's own house style.

**Files:**

- Create: `src/pdomain_ocr_labeler_spa/core/page_kind/reviewed_store.py`
- Test: `tests/unit/core/page_kind/test_reviewed_store.py`

**Interfaces:**

- Consumes: nothing beyond the standard library.
- Produces: `PageKindReviewedMarker` (`to_dict`/`from_dict`) and
  `PageKindReviewedStore(project_root: Path)` with
  `mark_reviewed(page_index, reviewed_at, *, actor="default", note=None) -> None`,
  `latest_for_page(page_index: int) -> PageKindReviewedMarker | None`, and
  `is_reviewed(page_index: int) -> bool`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/page_kind/test_reviewed_store.py
"""Unit tests for the per-page page-kind reviewed marker."""

from __future__ import annotations

from pathlib import Path


def test_a_marker_reads_back(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.page_kind.reviewed_store import PageKindReviewedStore

    store = PageKindReviewedStore(tmp_path)
    store.mark_reviewed(0, "2026-09-08T10:00:00+00:00", note="looks right")

    marker = store.latest_for_page(0)
    assert marker is not None
    assert marker.reviewed_at == "2026-09-08T10:00:00+00:00"
    assert marker.actor == "default"
    assert marker.note == "looks right"
    assert store.is_reviewed(0) is True


def test_an_unreviewed_page_has_no_marker(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.page_kind.reviewed_store import PageKindReviewedStore

    store = PageKindReviewedStore(tmp_path)
    assert store.latest_for_page(0) is None
    assert store.is_reviewed(0) is False


def test_the_most_recent_mark_wins_and_the_earlier_one_survives(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.page_kind.reviewed_store import PageKindReviewedStore

    store = PageKindReviewedStore(tmp_path)
    store.mark_reviewed(0, "2026-09-08T10:00:00+00:00", note="first pass")
    store.mark_reviewed(0, "2026-09-08T11:00:00+00:00", note="changed my mind")

    current = store.latest_for_page(0)
    assert current is not None
    assert current.note == "changed my mind"


def test_markers_for_different_pages_do_not_collide(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.page_kind.reviewed_store import PageKindReviewedStore

    store = PageKindReviewedStore(tmp_path)
    store.mark_reviewed(0, "2026-09-08T10:00:00+00:00")

    assert store.is_reviewed(0) is True
    assert store.is_reviewed(1) is False


def test_a_malformed_line_is_skipped_rather_than_failing_the_read(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.page_kind.reviewed_store import PageKindReviewedStore

    store = PageKindReviewedStore(tmp_path)
    store.mark_reviewed(0, "2026-09-08T10:00:00+00:00")
    path = tmp_path / ".pd-pages" / "page-kind-reviewed.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{not json\n")

    assert store.is_reviewed(0) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/page_kind/test_reviewed_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named '...core.page_kind.reviewed_store'`

- [ ] **Step 3: Write the implementation**

Create `src/pdomain_ocr_labeler_spa/core/page_kind/reviewed_store.py`:

```python
"""Append-only journal recording that a person reviewed one page's kind.

A page has one page kind, so the human's answer replaces the machine's whole
— diffing the confirmed value against ``PageKindProposalLog.latest_proposal_for_page``
already tells you accepted-or-changed. This store answers the other half:
whether anyone has looked at all. See pdomain-ocr-synth's docs/specs/2026-09-07-region-provenance-
and-persistence-design.md "Page kind needs a marker, not a decision log".
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PageKindReviewedMarker:
    """One record of a person looking at one page's kind."""

    page_index: int
    reviewed_at: str
    actor: str
    note: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_index": self.page_index,
            "reviewed_at": self.reviewed_at,
            "actor": self.actor,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PageKindReviewedMarker:
        return cls(
            page_index=int(d["page_index"]),
            reviewed_at=str(d["reviewed_at"]),
            actor=str(d.get("actor", "default")),
            note=str(d["note"]) if d.get("note") is not None else None,
        )


class PageKindReviewedStore:
    """Project-local JSONL journal of per-page review markers."""

    _RELATIVE_PATH: ClassVar[Path] = Path(".pd-pages") / "page-kind-reviewed.jsonl"

    def __init__(self, project_root: Path) -> None:
        self._path = Path(project_root) / self._RELATIVE_PATH

    @property
    def path(self) -> Path:
        return self._path

    def mark_reviewed(
        self, page_index: int, reviewed_at: str, *, actor: str = "default", note: str | None = None
    ) -> None:
        """Record that a person looked at this page's kind. Never rewrites a prior mark."""
        marker = PageKindReviewedMarker(
            page_index=page_index, reviewed_at=reviewed_at, actor=actor, note=note
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(marker.to_dict(), sort_keys=True) + "\n").encode("utf-8")
        fd = os.open(self._path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            os.write(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)

    def _read(self) -> list[PageKindReviewedMarker]:
        if not self._path.exists():
            return []
        markers: list[PageKindReviewedMarker] = []
        with self._path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    loaded = json.loads(stripped)
                except json.JSONDecodeError:
                    log.warning(
                        "page-kind-reviewed.jsonl: skipping malformed line %d", line_number
                    )
                    continue
                if isinstance(loaded, dict):
                    markers.append(PageKindReviewedMarker.from_dict(loaded))
        return markers

    def latest_for_page(self, page_index: int) -> PageKindReviewedMarker | None:
        """The most recent review marker for one page, or ``None`` if nobody has looked."""
        latest: PageKindReviewedMarker | None = None
        for marker in self._read():
            if marker.page_index == page_index:
                latest = marker
        return latest

    def is_reviewed(self, page_index: int) -> bool:
        return self.latest_for_page(page_index) is not None
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/core/page_kind/test_reviewed_store.py -v`
Expected: PASS, all five tests.

- [ ] **Step 5: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/core/page_kind/reviewed_store.py \
  tests/unit/core/page_kind/test_reviewed_store.py
git commit -m "feat(page-kind): add the per-page reviewed marker store"
```

---

### Task 6: The book-scoped `propose_page_kinds` job

Page kind cannot be decided from a single page — `fit_book_templates` measures every page's first
ink band before classifying any one page against the book's own fitted templates. That means it
cannot run at page fetch; it has to be a job, and job rows live in memory and are lost on restart
(`core/jobs/runner.py`'s own docstring), so the handler writes each page's proposal durably via
`PageKindProposalLog` (Task 4) as it goes, treating the job row as progress reporting only.

The labeler has no image-measurement pipeline of its own — that is exactly what
`pdomain-pgdp-measure` is for — so this task adds it as a dependency and calls its public
`profile_page`, `fit_book_templates`, and `classify_pages` directly against
`Project.image_paths`. Nothing else in the labeler or `pdomain-prep-for-pgdp` consumes
`pdomain-pgdp-measure` as a package today, so this is new plumbing, not an existing wire.

**Files:**

- Create: `src/pdomain_ocr_labeler_spa/core/jobs/handlers/propose_page_kinds.py`
- Modify: `src/pdomain_ocr_labeler_spa/core/jobs/runner.py`
- Modify: `src/pdomain_ocr_labeler_spa/api/projects.py`
- Modify: `pyproject.toml`
- Test: `tests/unit/core/jobs/test_propose_page_kinds_handler.py`
- Test: `tests/unit/api/test_propose_page_kinds_endpoint.py`

**Interfaces:**

- Consumes: `PageKindProposal`, `PageKindProposalRun` (Task 3), `PageKindProposalLog` (Task 4),
  `pdomain_pgdp_measure.profiling.profile_page`,
  `pdomain_pgdp_measure.page_templates.{PAGE_TEMPLATE_METHOD, fit_book_templates, classify_pages}`,
  `pdomain_pgdp_measure.profile_input.ProfileInputPage`.
- Produces: `handle_propose_page_kinds(runner, job) -> None`, registered as job type
  `"propose_page_kinds"`; `POST /api/projects/{project_id}/propose-page-kinds` → `202 {job_id}`.

- [ ] **Step 1: Add the dependency**

In `pyproject.toml`, add `pdomain-pgdp-measure` next to the other suite packages:

```toml
    "pdomain-book-tools==0.27.0",
    "pdomain-book-contracts>=0.1.0",
    "pdomain-pgdp-measure>=0.1.0",
```

And to `[tool.uv.sources]`, following the same private-index pattern as its siblings — verify this
package publishes to `pdomain-index-pip` the same way before running `uv lock`; if it does not, use
whichever index it does publish to instead:

```toml
[tool.uv.sources]
pdomain-book-tools = { index = "pdomain-index-pip" }
pdomain-book-contracts = { index = "pdomain-index-pip" }
pdomain-ops = { index = "pdomain-index-pip" }
pdomain-pgdp-measure = { index = "pdomain-index-pip" }
```

Run: `uv lock`
Expected: resolves without conflict — `pdomain-pgdp-measure`'s only runtime dependencies are
`pydantic`, `pillow`, `numpy`, all already present transitively via `pdomain-book-tools`.

- [ ] **Step 2: Write the failing test**

```python
# tests/unit/core/jobs/test_propose_page_kinds_handler.py
"""Unit tests for the propose_page_kinds job handler."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pdomain_pgdp_measure.profile_models import CoordinateFrame, InkBand, PageMeasurement

from pdomain_ocr_labeler_spa.core.jobs.events import JobEventBroker
from pdomain_ocr_labeler_spa.core.jobs.runner import Job, JobRunner
from pdomain_ocr_labeler_spa.core.models import Project
from pdomain_ocr_labeler_spa.core.notifications import NotificationQueue
from pdomain_ocr_labeler_spa.core.page_kind.proposal_log import PageKindProposalLog
from pdomain_ocr_labeler_spa.core.project_state import ProjectState

_WIDTH = 1000
_HEIGHT = 1600


def _measured(page_name: str, *, first_band_top: int, bands: int = 24) -> PageMeasurement:
    """A minimal measured page, evenly banded from a given top.

    Mirrors pdomain-pgdp-measure's own ``tests/test_pgdp_page_templates.py::_page``.
    """
    ink_bands = tuple(
        InkBand(y_start=first_band_top + i * 40, y_end=first_band_top + i * 40 + 26)
        for i in range(bands)
    )
    bottom = ink_bands[-1].y_end
    return PageMeasurement(
        page_name=page_name,
        source_path=f"bookA/{page_name}",
        sha256="a" * 64,
        source_frame=CoordinateFrame(width=_WIDTH, height=_HEIGHT),
        image_mode="L",
        grayscale_threshold=127,
        foreground_pixels=1000,
        foreground_bounds=(80, first_band_top, 920, bottom),
        margins=(80, first_band_top, 80, _HEIGHT - bottom),
        ink_bands=ink_bands,
    )


def _project(tmp_path: Path, page_count: int) -> Project:
    image_paths = [tmp_path / f"{i:03d}.png" for i in range(page_count)]
    for path in image_paths:
        path.write_bytes(b"")
    return Project(
        project_id="bookA", project_root=tmp_path, image_paths=image_paths,
        ground_truth_map={}, total_pages=page_count,
    )


def _runner_and_job(project: Project, tops: list[int]) -> tuple[JobRunner, Job]:
    project_state = ProjectState()
    project_state.set_loaded_project(project)

    def _measure_fn(project_id: str, page: object) -> PageMeasurement:
        name = getattr(page, "name")
        index = int(name.split(".")[0])
        return _measured(name, first_band_top=tops[index])

    runner = JobRunner(
        JobEventBroker(),
        context={
            "project_state": project_state,
            "notification_queue": NotificationQueue(),
            "propose_page_kinds_measure_fn": _measure_fn,
        },
    )
    job = Job(job_id="j1", job_type="propose_page_kinds", created_at=datetime.now(UTC))
    return runner, job


async def test_a_steady_book_proposes_body_for_every_page(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.jobs.handlers.propose_page_kinds import (
        handle_propose_page_kinds,
    )

    project = _project(tmp_path, 4)
    runner, job = _runner_and_job(project, tops=[300, 302, 298, 301])

    await handle_propose_page_kinds(runner, job)

    proposal_log = PageKindProposalLog(project.project_root)
    runs = proposal_log.runs()
    assert len(runs) == 1
    proposals = proposal_log.proposals_for_run(runs[0].run_id)
    assert len(proposals) == 4
    assert all(p.kind.value == "body" for p in proposals)
    assert all(p.confidence == 1.0 for p in proposals)


async def test_a_sunk_page_proposes_chapter_opening(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.jobs.handlers.propose_page_kinds import (
        handle_propose_page_kinds,
    )

    project = _project(tmp_path, 5)
    runner, job = _runner_and_job(project, tops=[300, 302, 298, 301, 470])

    await handle_propose_page_kinds(runner, job)

    proposal = PageKindProposalLog(project.project_root).latest_proposal_for_page(4)
    assert proposal is not None
    assert proposal.kind.value == "chapter opening"


async def test_the_job_never_touches_the_page_blob(tmp_path: Path) -> None:
    """The page blob is only ever written by a human action — a classifier run is not one."""
    from pdomain_ocr_labeler_spa.core.jobs.handlers.propose_page_kinds import (
        handle_propose_page_kinds,
    )

    project = _project(tmp_path, 3)
    runner, job = _runner_and_job(project, tops=[300, 302, 298])
    blobs_dir = project.project_root / ".pd-pages" / "blobs"

    await handle_propose_page_kinds(runner, job)

    assert not blobs_dir.exists()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/jobs/test_propose_page_kinds_handler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named '...core.jobs.handlers.propose_page_kinds'`

- [ ] **Step 4: Write the handler**

Create `src/pdomain_ocr_labeler_spa/core/jobs/handlers/propose_page_kinds.py`:

```python
"""propose_page_kinds job handler.

Spec authority: pdomain-ocr-synth's docs/specs/2026-09-07-region-provenance-and-persistence-
design.md "Page kind is classified per book, and it runs before regions".

The pass needs every page before it can classify any — ``fit_book_templates``
measures the whole book's first-band geometry before classifying a single
page against it — so it cannot run at page fetch; it is a book-scoped job.
Job rows live in memory and are lost on restart, so this handler writes each
page's proposal durably via ``PageKindProposalLog`` as it goes, and treats
the job row purely as progress reporting.

This handler never touches ``Page.page_kind`` and never calls
``save_page_content_to_store`` — the page blob is only ever written by a
human action, and a classifier run is not one. Only the page-kind confirm
route does either.

Handler entry-point: ``handle_propose_page_kinds(runner, job)`` — registered
in ``core/jobs/runner._HANDLERS["propose_page_kinds"]``.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol

from pdomain_book_contracts.annotation import PageKind
from pdomain_pgdp_measure.page_templates import (
    PAGE_TEMPLATE_METHOD,
    PageClassification,
    classify_pages,
    fit_book_templates,
)
from pdomain_pgdp_measure.profile_input import ProfileInputPage
from pdomain_pgdp_measure.profile_models import PageMeasurement
from pdomain_pgdp_measure.profiling import profile_page

from ...notifications import NotificationKind, NotificationQueue
from ...page_kind.models import PageKindProposal, PageKindProposalRun
from ...page_kind.proposal_log import PageKindProposalLog
from ...project_state import ProjectState

if TYPE_CHECKING:
    from ..runner import Job, JobRunner

log = logging.getLogger(__name__)


class _MeasurePageFn(Protocol):
    def __call__(self, project_id: str, page: ProfileInputPage) -> PageMeasurement: ...


# pdomain-pgdp-measure.page_templates.PageClass values -> PageKind. Not a
# vocabulary merge: PageClass is a measured signal that only ever proposes,
# never decides, what a page is. See the spec's "Three page vocabularies
# already exist, and they are different axes".
_PAGE_CLASS_TO_KIND: dict[str, PageKind] = {
    "normal_recto": PageKind.BODY,
    "normal_verso": PageKind.BODY,
    "chapter_opening": PageKind.CHAPTER_OPENING,
    "unknown": PageKind.UNKNOWN,
}


def _get_required_context(
    runner: JobRunner,
) -> tuple[ProjectState, NotificationQueue, _MeasurePageFn]:
    ctx: dict[str, Any] = runner.context
    project_state = ctx.get("project_state")
    notification_queue = ctx.get("notification_queue")
    if not isinstance(project_state, ProjectState):
        raise RuntimeError("propose_page_kinds: runner.context['project_state'] is not wired")
    if not isinstance(notification_queue, NotificationQueue):
        raise RuntimeError("propose_page_kinds: runner.context['notification_queue'] is not wired")
    # Test injection point, mirroring auto_rotate_all's "auto_rotate_ocr_fn" —
    # production always measures the real image on disk via profile_page.
    measure_fn: _MeasurePageFn = ctx.get("propose_page_kinds_measure_fn") or profile_page
    return project_state, notification_queue, measure_fn


def _to_kind(classification: PageClassification) -> PageKind:
    return _PAGE_CLASS_TO_KIND.get(classification.page_class, PageKind.UNKNOWN)


async def handle_propose_page_kinds(runner: JobRunner, job: Job) -> None:
    """Classify every page of the active project's book and record proposals."""
    project_state, notification_queue, measure_fn = _get_required_context(runner)
    project = project_state.loaded_project
    if project is None:
        await runner.update_progress(job.job_id, current=0, total=0, message="No project loaded")
        return

    total = project.total_pages
    log.info(
        "propose_page_kinds: project=%s pages=%d job=%s", project.project_id, total, job.job_id
    )
    await runner.update_progress(job.job_id, current=0, total=total, message=f"Measuring {total} page(s)")

    measured: list[PageMeasurement] = []
    for page_index, image_path in enumerate(project.image_paths):
        input_page = ProfileInputPage(
            name=image_path.name,
            image_path=image_path,
            source_path=f"{project.project_id}/{image_path.name}",
        )
        measured.append(measure_fn(project.project_id, input_page))
        await runner.update_progress(
            job.job_id, current=page_index + 1, total=total,
            message=f"Measured page {page_index + 1}/{total}",
        )

    templates = fit_book_templates(measured)
    # classify_pages preserves input order, so zipping with range(total)
    # recovers page_index without depending on page_name uniqueness.
    classifications = classify_pages(measured, templates)

    run = PageKindProposalRun(
        run_id=uuid.uuid4().hex,
        model_id="pgdp-measure/page-templates",
        model_version=PAGE_TEMPLATE_METHOD,
        created_at=datetime.now(UTC).isoformat(),
        page_count=total,
    )
    proposals = [
        PageKindProposal(
            proposal_id=uuid.uuid4().hex,
            run_id=run.run_id,
            page_index=page_index,
            kind=_to_kind(classification),
            confidence=classification.confidence,
            evidence={
                "page_class": classification.page_class,
                "template_residual_px": classification.template_residual_px,
            },
        )
        for page_index, classification in enumerate(classifications)
    ]

    proposal_log = PageKindProposalLog(project.project_root)
    proposal_log.append_run(run)
    proposal_log.append_proposals(proposals)

    job.payload["run_id"] = run.run_id
    job.payload["proposal_count"] = len(proposals)
    notification_queue.queue(
        NotificationKind.POSITIVE,
        f"Proposed page kinds for {len(proposals)} page(s) in project {project.project_id}.",
    )


__all__ = ["handle_propose_page_kinds"]
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/unit/core/jobs/test_propose_page_kinds_handler.py -v`
Expected: PASS, all three tests.

- [ ] **Step 6: Register the handler**

In `src/pdomain_ocr_labeler_spa/core/jobs/runner.py`, add the wrapper right after
`_handle_refine_bboxes`:

```python
async def _handle_propose_page_kinds(runner: JobRunner, job: Job) -> None:
    """propose_page_kinds handler — delegates to
    ``core/jobs/handlers/propose_page_kinds``.

    Classifies every page of the active project's book via pgdp-measure's
    book-scoped page-template classifier and records proposals durably.
    """
    from .handlers.propose_page_kinds import handle_propose_page_kinds  # lazy import

    await handle_propose_page_kinds(runner, job)
```

Add it to `_HANDLERS`:

```python
_HANDLERS: dict[str, Handler] = {
    "reload_ocr": _handle_reload_ocr,
    "save_project": _handle_save_project,
    "export": _handle_export,
    "rotate_page": _handle_rotate_page,
    "auto_rotate_all": _handle_auto_rotate_all,
    "refine_bboxes": _handle_refine_bboxes,
    "propose_page_kinds": _handle_propose_page_kinds,
}
```

- [ ] **Step 7: Add the start-job route**

In `src/pdomain_ocr_labeler_spa/api/projects.py`, add the response model near
`AutoRotateAllResponse`:

```python
class ProposePageKindsResponse(BaseModel):
    """Response for ``POST /api/projects/{id}/propose-page-kinds`` → 202."""

    job_id: str
```

Add the route, mirroring `post_auto_rotate_all`:

```python
@router.post(
    "/{project_id}/propose-page-kinds", status_code=202, response_model=ProposePageKindsResponse
)
def post_propose_page_kinds(
    project_id: str,
    project_state: ProjectState = Depends(get_project_state),
    runner: JobRunner = Depends(get_job_runner),
) -> JSONResponse:
    """``POST /api/projects/{id}/propose-page-kinds`` → ``202 {job_id}``.

    Enqueues a ``propose_page_kinds`` job that measures every page's image,
    classifies the whole book against its own fitted templates, and records
    one page-kind proposal per page.

    Spec: pdomain-ocr-synth's docs/specs/2026-09-07-region-provenance-and-persistence-design.md
    "Page kind is classified per book, and it runs before regions".

    Returns 404 when the requested project is not loaded.
    """
    project = project_state.loaded_project
    if project is None or project.project_id != project_id:
        return JSONResponse(
            status_code=404,
            content=ApiError(
                error="project_not_found",
                message=f"project not found or not loaded: {project_id}",
            ).model_dump(),
        )

    job_id = runner.submit(
        "propose_page_kinds",
        project_id=project_id,
        payload={"project_id": project_id, "page_count": project.total_pages},
    )
    return JSONResponse(status_code=202, content={"job_id": job_id})
```

- [ ] **Step 8: Write the route test**

```python
# tests/unit/api/test_propose_page_kinds_endpoint.py
"""Unit tests for POST /api/projects/{id}/propose-page-kinds."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pdomain_ocr_labeler_spa.bootstrap import build_app
from pdomain_ocr_labeler_spa.settings import Settings


def _make_settings(tmp_path: Path, **overrides: object) -> Settings:
    base: dict[str, object] = {
        "host": "127.0.0.1",
        "port": 8080,
        "config_root": tmp_path / "config",
        "data_root": tmp_path / "data",
        "cache_root": tmp_path / "cache",
        "mode": "api_only",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


@pytest.fixture
def projects_root(tmp_path: Path) -> Path:
    root = tmp_path / "projects"
    root.mkdir()
    proj = root / "book1"
    proj.mkdir()
    (proj / "001.png").write_bytes(b"\x89PNG\r\n")
    return root


@pytest.fixture
def loaded_client(tmp_path: Path, projects_root: Path) -> Iterator[TestClient]:
    settings = _make_settings(tmp_path, source_projects_root=projects_root)
    app = build_app(settings)
    with TestClient(app) as c:
        resp = c.post("/api/projects/load", json={"project_root": str(projects_root / "book1")})
        assert resp.status_code == 200, resp.text
        yield c


def test_propose_page_kinds_returns_a_job_id(loaded_client: TestClient) -> None:
    resp = loaded_client.post("/api/projects/book1/propose-page-kinds")
    assert resp.status_code == 202, resp.text
    assert "job_id" in resp.json()


def test_propose_page_kinds_404s_when_project_not_loaded(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    app = build_app(settings)
    with TestClient(app) as client:
        resp = client.post("/api/projects/unknown-book/propose-page-kinds")
        assert resp.status_code == 404
```

- [ ] **Step 9: Run the tests**

Run: `uv run pytest tests/unit/api/test_propose_page_kinds_endpoint.py -v`
Expected: PASS, both tests.

- [ ] **Step 10: Run the full suite and the gate**

Run: `make test`
Expected: PASS with no regression.

Run: `make AI=1 ci`
Expected: PASS.

- [ ] **Step 11: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/core/jobs/handlers/propose_page_kinds.py \
  src/pdomain_ocr_labeler_spa/core/jobs/runner.py src/pdomain_ocr_labeler_spa/api/projects.py \
  pyproject.toml uv.lock tests/unit/core/jobs/test_propose_page_kinds_handler.py \
  tests/unit/api/test_propose_page_kinds_endpoint.py
git commit -m "feat(page-kind): add the book-scoped propose_page_kinds job and its start route"
```

---

### Task 7: The confirm route

A page has one kind, so confirming it is the human action that writes `Page.page_kind` — the only
place the page blob is written for this level, mirroring `update_word_ground_truth` in
`api/words.py`. It then marks the reviewed store (Task 5). This task depends on Task 1 having
shipped and released in `pdomain-book-tools`, and on this repo's pin being bumped to consume it.

The confirm response attaches the confirmed kind onto `PagePayload.extra` via `model_copy` — it
does not touch `_page_payload` itself, so a plain `GET` still returns whatever it already returns
today. Wiring `page_kind` into every `GET` is left to a follow-up, the same way the region-stores
plan deferred full route/payload wiring to its own next plan.

**Files:**

- Modify: `src/pdomain_ocr_labeler_spa/api/pages.py`
- Modify: `pyproject.toml` (bump the `pdomain-book-tools` pin)
- Test: `tests/unit/api/test_page_kind_endpoint.py`

**Interfaces:**

- Consumes: `PageKindReviewedStore` (Task 5), `PageKind` from `pdomain_book_contracts.annotation`.
- Produces: `POST /api/projects/{project_id}/pages/{page_index}/page-kind` → `PagePayload`.

- [ ] **Step 1: Bump the book-tools pin**

Determine the version `pdomain-book-tools` was tagged with after Task 1's commit (for example
`git -C ../pdomain-book-tools describe --tags` against its released state), then update the pin in
`pyproject.toml`:

```toml
    "pdomain-book-tools==<new-version>",
```

Run: `uv lock`
Expected: resolves with `PageKind` importable via `pdomain_book_tools.ocr.page.Page.page_kind`.

- [ ] **Step 2: Write the failing test**

```python
# tests/unit/api/test_page_kind_endpoint.py
"""Unit tests for POST .../pages/{idx}/page-kind — confirming a page kind.

Pattern mirrors tests/unit/api/test_rematch_gt.py: seed a real Page into
PageState via project_state._page_states, then POST through a real TestClient.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pdomain_book_tools.ocr.page import Page

from pdomain_ocr_labeler_spa.bootstrap import build_app
from pdomain_ocr_labeler_spa.core.page_kind.reviewed_store import PageKindReviewedStore
from pdomain_ocr_labeler_spa.core.page_state import PageLoadOutcome, PageSource
from pdomain_ocr_labeler_spa.core.project_state import PageState
from pdomain_ocr_labeler_spa.settings import Settings


def _make_settings(tmp_path: Path, **overrides: object) -> Settings:
    base: dict[str, object] = {
        "host": "127.0.0.1",
        "port": 8080,
        "config_root": tmp_path / "config",
        "data_root": tmp_path / "data",
        "cache_root": tmp_path / "cache",
        "mode": "api_only",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


@pytest.fixture
def projects_root(tmp_path: Path) -> Path:
    root = tmp_path / "projects"
    root.mkdir()
    proj = root / "book1"
    proj.mkdir()
    (proj / "001.png").write_bytes(b"\x89PNG\r\n")
    return root


@pytest.fixture
def loaded_client(tmp_path: Path, projects_root: Path) -> Iterator[TestClient]:
    settings = _make_settings(tmp_path, source_projects_root=projects_root)
    app = build_app(settings)
    with TestClient(app) as c:
        resp = c.post("/api/projects/load", json={"project_root": str(projects_root / "book1")})
        assert resp.status_code == 200, resp.text
        yield c


def _seed_page_state(client: TestClient, *, page_index: int, page: Page) -> PageState:
    project_state = client.app.state.project_state  # type: ignore[attr-defined]
    outcome = PageLoadOutcome(page_index=page_index, source=PageSource.OCR, payload=page)
    pstate = PageState(page_index=page_index, page_record=outcome)
    pstate.generation = 1
    project_state._page_states[page_index] = pstate
    return pstate


def test_confirming_a_page_kind_writes_it_and_marks_it_reviewed(
    loaded_client: TestClient, projects_root: Path
) -> None:
    page = Page(width=100, height=100, page_index=0, blocks=[])
    pstate = _seed_page_state(loaded_client, page_index=0, page=page)
    gen_before = pstate.generation

    resp = loaded_client.post(
        "/api/projects/book1/pages/0/page-kind",
        json={"kind": "title page", "note": "looks right"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["extra"]["page_kind"] == "title page"
    assert body["extra"]["page_kind_reviewed"] is True
    assert page.page_kind.value == "title page"
    assert pstate.generation == gen_before + 1

    reviewed = PageKindReviewedStore(projects_root / "book1").latest_for_page(0)
    assert reviewed is not None
    assert reviewed.note == "looks right"


def test_confirming_an_invalid_page_kind_returns_400(loaded_client: TestClient) -> None:
    page = Page(width=100, height=100, page_index=0, blocks=[])
    _seed_page_state(loaded_client, page_index=0, page=page)

    resp = loaded_client.post(
        "/api/projects/book1/pages/0/page-kind", json={"kind": "not-a-real-kind"}
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"] == "invalid_page_kind"


def test_confirming_a_page_kind_on_an_unloaded_page_returns_400(loaded_client: TestClient) -> None:
    resp = loaded_client.post("/api/projects/book1/pages/0/page-kind", json={"kind": "body"})
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"] == "page_not_loaded"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/unit/api/test_page_kind_endpoint.py -v`
Expected: FAIL with a 404 (route does not exist yet).

- [ ] **Step 4: Write the implementation**

In `src/pdomain_ocr_labeler_spa/api/pages.py`, add `from datetime import UTC, datetime` to the
imports if not already present. Add the request model near `RematchGtRequest`:

```python
class ConfirmPageKindRequest(BaseModel):
    """Body for ``POST .../page-kind`` — the human's confirmed page kind."""

    kind: str
    note: str | None = None
```

Add the route, following `rematch_gt`'s exact inline persist-and-error-handle style:

```python
@router.post("/{page_index}/page-kind", response_model=PagePayload)
def confirm_page_kind(
    *,
    project_id: str,
    page_index: int,
    body: ConfirmPageKindRequest,
    project_state: ProjectState = Depends(get_project_state),
    settings: Settings = Depends(get_settings),
    app_config: AppConfig = Depends(get_app_config),
    page_store: LabelerPageStore | None = Depends(get_page_store_optional),
) -> JSONResponse:
    """``POST .../page-kind`` — record a person's confirmed page kind.

    Spec: pdomain-ocr-synth's docs/specs/2026-09-07-region-provenance-and-persistence-design.md
    "Page kind needs a marker, not a decision log". A page has one kind, so
    the human's answer replaces the machine's whole outright — there is no
    accept/reject pair here the way there is for regions. Writing
    ``page.page_kind`` under the per-page lock and re-serializing via
    ``save_page_content_to_store`` is what "the page blob is only ever
    written by a human action" means at this level; ``propose_page_kinds``
    (a machine job) never touches either.
    """
    from pdomain_book_contracts.annotation import PageKind

    from ..core.page_kind.reviewed_store import PageKindReviewedStore

    err = _check_project_and_page(project_id, page_index, project_state)
    if err is not None:
        return err

    try:
        kind = PageKind(body.kind)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content=ApiError(
                error="invalid_page_kind",
                message=f"not a valid page kind: {body.kind!r}",
            ).model_dump(),
        )

    project = project_state.loaded_project
    if project is None:  # _check_project_and_page guarantees; explicit to survive -O
        raise RuntimeError("project is None after _check_project_and_page passed — invariant violated")

    pstate = project_state.get_page_state(page_index)
    if pstate is None or pstate.page_record is None:
        return JSONResponse(
            status_code=400,
            content=ApiError(
                error="page_not_loaded",
                message=f"page {page_index} has no in-memory page record; load or run OCR first",
            ).model_dump(),
        )
    page = getattr(pstate.page_record, "payload", None)
    if page is None:
        return JSONResponse(
            status_code=400,
            content=ApiError(
                error="page_not_loaded",
                message=f"page {page_index} record carries no payload; load or run OCR first",
            ).model_dump(),
        )

    page_lock = project_state.get_page_lock(page_index)
    with page_lock:
        page.page_kind = kind
        pstate.generation += 1

        if page_store is not None and pstate.page_id is not None and callable(
            getattr(page, "to_dict", None)
        ):
            try:
                save_page_content_to_store(
                    page_id=pstate.page_id,
                    page=page,
                    store=page_store,
                    changes=[{"type": "page_kind", "page_index": page_index, "kind": kind.value}],
                    labeler_sidecars=pstate,
                )
            except Exception as exc:
                log.warning(
                    "confirm_page_kind: store write failed page_id=%s: %s", pstate.page_id, exc
                )
                return JSONResponse(
                    status_code=503,
                    content=ApiError(
                        error="store_persist_failed",
                        message=(
                            f"page kind applied in memory but failed to persist page "
                            f"{page_index} to the event store: {exc}"
                        ),
                    ).model_dump(),
                )

        PageKindReviewedStore(project.project_root).mark_reviewed(
            page_index, datetime.now(UTC).isoformat(), note=body.note
        )

    payload = _page_payload(
        project_id=project_id,
        page_index=page_index,
        project_state=project_state,
        settings=settings,
        app_config=app_config,
        page_store=page_store,
    )
    updated = payload.model_copy(
        update={
            "extra": {**payload.extra, "page_kind": kind.value, "page_kind_reviewed": True},
        }
    )
    return JSONResponse(status_code=200, content=updated.model_dump(mode="json"))
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/unit/api/test_page_kind_endpoint.py -v`
Expected: PASS, all three tests.

- [ ] **Step 6: Run the full suite and the gate**

Run: `make test`
Expected: PASS with no regression.

Run: `make AI=1 ci`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/api/pages.py pyproject.toml uv.lock \
  tests/unit/api/test_page_kind_endpoint.py
git commit -m "feat(page-kind): confirm a page's kind and mark it reviewed"
```

---

## What this plan does not do

- It does not wire `page_kind` (or the reviewed marker) onto `_page_payload`'s regular `GET`
  response. The confirm route echoes the value it just wrote; seeing it on every subsequent fetch
  is a follow-up, the same way the region-stores plan deferred full `PagePayload` growth.
- It builds no review queue or triage UI for pages the classifier declined (`kind=UNKNOWN`,
  `confidence=None`). That is slice 5 of the labeling track roadmap, not this plan.
- It does not condition region proposals on a confirmed page kind, or invalidate stale region
  proposals when a page kind is relabeled. That is the region proposal engine (slice 4), gated on
  this plan and on the page-template spread, per the design's "A proposal run records what it was
  conditioned on".
- It does not give `pdomain-pgdp-measure` a pluggable book-scoped classifier seam analogous to
  `register_detector`. `fit_book_templates` stays a fitted heuristic; only its output gains a
  confidence.
- It does not add any frontend surface for reviewing or confirming a page kind. Only the backend
  route exists after this plan.
- It does not touch `pdomain-prep-for-pgdp`'s `PageType` or `StageReviewStore`. Those are read here
  only as reference for the marker shape and are not modified.

## Related

- [Annotation provenance and
  persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md) — the design this
  plan carries out for page kind specifically.
- [Annotation vocabularies in
  book-contracts](2026-09-08-annotation-vocabularies-in-book-contracts.md) — ships `PageKind`. Must
  land before Task 1 of this plan.
- [Annotation preconditions in book-tools and
  measure](2026-09-08-annotation-preconditions-in-book-tools-and-measure.md) — ships
  `PageTemplate.first_band_spread_px`. Must land before Task 2 of this plan.
- [Region stores and resolver](2026-09-08-region-stores-and-resolver.md) — the equivalent
  three-store treatment for regions; the reviewed-marker-only shape here is the deliberately
  lighter counterpart the design calls for at this level.
- [Labeling track roadmap](2026-09-07-labeling-track-roadmap.md) — the seven slices; page kind is
  slice 1's deliverable, this plan is what slice 2 needed to be able to condition on it.
