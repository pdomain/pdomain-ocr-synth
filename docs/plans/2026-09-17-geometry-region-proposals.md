---
Status: active
Owner: CT
Created: 2026-09-17
Last verified: 2026-09-17
Kind: plan
---

# Geometry Region Proposals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the `propose_regions` job produce real region proposals by measuring each book the
way the page-kind job already does and turning its top furniture bands into `page header` and
`page number` proposals.

**Architecture:** The detector seam Task 5 of the region-routes plan built takes only a `Page`,
which is not enough. Widen it to take one input object carrying the page, its index, its
classification, and the book's fitted templates. Then have `propose_regions` measure the book with
`profile_page`, fit it with `fit_book_templates`, classify it with `classify_pages`, and hand each
page to the detector. The detector reads the page's own word boxes inside each furniture band's y
range, clusters them horizontally, and proposes one region per cluster.

**Tech Stack:** Python 3.13, FastAPI, pydantic, pytest, ruff, basedpyright.

**Spec:** [Geometry region proposals](../specs/2026-09-17-geometry-region-proposals-design.md).

## Agent Index

- **Kind:** plan
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-17
- **Last verified:** 2026-09-17
- **Provenance:** authored 2026-09-17 from the design above and direct inspection of
  `pdomain-ocr-labeler-spa` `core/regions/detector.py`, `core/jobs/handlers/propose_regions.py`,
  `core/jobs/handlers/propose_page_kinds.py`, `core/regions/block_adapter.py`, `api/regions.py`,
  `bootstrap.py`; `pdomain-pgdp-measure` `page_templates.py`, `profile_models.py`,
  `profile_input.py`; `pdomain-book-tools` `ocr/page.py`, `ocr/block.py`, `ocr/word.py`; and
  `pdomain-book-contracts` `annotation` and `geometry/bounding_box.py`
- **Disposition:** Active. Slice 4 of the labeling track, first increment. Produces the first
  machine-generated region proposals in the system.
- **Read when:** building the region detector, changing the detector seam, or touching the
  `propose_regions` job's measurement pass.
- **Search terms:** slice 4, geometry detector, furniture detector, DetectorInput, page header,
  page number, running head, folio, furniture_band_ordinals, BookTemplates.

## Global Constraints

- Python floor is `>=3.13,<3.14`. Warnings are errors (`filterwarnings = ["error", ...]` in
  `pyproject.toml`). Always construct a `Page` with `Page(blocks=[...])` or `Page.from_dict(...)`,
  never `Page(items=...)` — that alias raises `DeprecationWarning` and therefore fails.
- Run `make AI=1 test` before committing. The baseline on `master` at `8fd6a02` is 1645 passed and
  4 skipped. The 4 skips are Docker-build tests that need `pnpm` on `PATH`; that is expected.
- Committing needs the venv on `PATH`. Prefix with `export PATH="$PWD/.venv-container/bin:$PATH"`
  or the pre-commit hook fails with `pre-commit not found`.
- Commit subjects must stay within 72 characters or gitlint rejects the commit.
- **The page blob is only ever written by a human action.** Nothing in this plan may call
  `save_page_content_to_store` or `save_page_to_store`. A proposal is a machine's claim.
- **The job must stay off the event loop.** `profile_page` decodes an image and scans it with
  numpy, and the detector reads word boxes over a whole page. Every per-page call goes through
  `await asyncio.to_thread(...)`, the way `propose_page_kinds` and `propose_regions` already do.
- **`Page.is_content_normalized` raises `ValueError` on a page that mixes normalized and pixel
  word boxes.** Ink bands are in source-frame pixels, so a detector comparing a normalized word box
  against a band y range would be comparing 0.42 against 300. Every task that reads a word box
  must resolve this, and the answer is in Task 3.
- **`RegionRole.PAGE_HEADER` is `"page header"` and `RegionRole.PAGE_NUMBER` is `"page number"`.**
  Both are among the original 20 roles in `Block.ALLOWED_BLOCK_ROLE_LABELS`, so neither can raise
  the `invalid_region_role` path. Verified against `pdomain-book-tools` v0.28.0, which the labeler
  pins.
- `tests/unit/.../test_static_mounts.py` fails intermittently under `pytest -n auto` because xdist
  workers share one real `static/` directory. It is pre-existing and unrelated. Do not chase it.
- No route or response model changes in this plan, so `make openapi-export` should produce no diff.
  Run it to confirm and report if it does.

## File Structure

| file | responsibility |
| --- | --- |
| `src/pdomain_ocr_labeler_spa/core/regions/detector.py` | The seam. `DetectedRegion`, the new `DetectorInput`, the `RegionDetector` type, `null_region_detector`. Nothing that measures. |
| `src/pdomain_ocr_labeler_spa/core/regions/furniture.py` | New. The furniture detector and its helpers. The only file that knows what a running head looks like. |
| `src/pdomain_ocr_labeler_spa/core/page_measurement.py` | New. One shared measure-and-fit pass over a book, extracted from `propose_page_kinds`. Both jobs call it. |
| `src/pdomain_ocr_labeler_spa/core/jobs/handlers/propose_regions.py` | Modified. Calls the shared pass, builds a `DetectorInput` per page, hands it to the detector. |
| `src/pdomain_ocr_labeler_spa/core/jobs/handlers/propose_page_kinds.py` | Modified. Calls the shared pass instead of its own inline loop. |
| `src/pdomain_ocr_labeler_spa/bootstrap.py` | Modified. Wires the furniture detector into `JobRunner.context["region_detector"]`. |

`furniture.py` is separate from `detector.py` on purpose. `detector.py` is a seam every future
detector imports; a file that also contains one detector's heuristics invites the next one to be
added beside it until the seam and its implementations cannot be told apart.

---

### Task 1: Widen the detector seam

The seam takes a bare `Page` today. A furniture detector needs the page's index to find that page's
classification, and the book's templates to know where the head band belongs and how wide the text
block is. This task changes the shape and nothing else, so it is separately reviewable and the
suite must stay green with no behaviour change.

**Files:**

- Modify: `src/pdomain_ocr_labeler_spa/core/regions/detector.py`
- Modify: `src/pdomain_ocr_labeler_spa/core/jobs/handlers/propose_regions.py`
- Test: `tests/unit/core/regions/test_detector.py`

**Interfaces:**

- Consumes: `Page` from `pdomain_book_tools.ocr.page`; `PageClassification` and `BookTemplates`
  from `pdomain_pgdp_measure.page_templates`; `PageMeasurement` from
  `pdomain_pgdp_measure.profile_models`; `RegionRole` from `pdomain_book_contracts.annotation`.
- Produces: `DetectorInput` (frozen dataclass with fields `page: Page`, `page_index: int`,
  `measurement: PageMeasurement`, `classification: PageClassification`, `templates: BookTemplates`);
  `RegionDetector = Callable[[DetectorInput], Sequence[DetectedRegion]]`;
  `null_region_detector(detector_input: DetectorInput) -> list[DetectedRegion]`.

- [ ] **Step 1: Write the failing test**

Replace the whole body of `tests/unit/core/regions/test_detector.py` with this.

```python
"""Unit tests for the pluggable region detector interface."""

from __future__ import annotations


def _empty_detector_input() -> object:
    from pdomain_book_tools.ocr.page import Page
    from pdomain_pgdp_measure.page_templates import BookTemplates, PageClassification
    from pdomain_pgdp_measure.profile_models import PageMeasurement

    from pdomain_ocr_labeler_spa.core.regions.detector import DetectorInput

    return DetectorInput(
        page=Page(width=200, height=300, page_index=0, blocks=[]),
        page_index=0,
        measurement=PageMeasurement(
            page_name="001.png",
            source_path="book1/001.png",
            sha256=None,
            source_frame=None,
            image_mode=None,
            grayscale_threshold=None,
            foreground_pixels=None,
            foreground_bounds=None,
            margins=None,
        ),
        classification=PageClassification("001.png", "unknown", None, ()),
        templates=BookTemplates(None, None, None, (), 0.0),
    )


def test_the_null_detector_proposes_nothing() -> None:
    from pdomain_ocr_labeler_spa.core.regions.detector import null_region_detector

    assert null_region_detector(_empty_detector_input()) == []


def test_detector_input_carries_the_page_index_and_the_book_templates() -> None:
    """The seam's whole reason to widen: a detector needs more than one page."""
    from pdomain_pgdp_measure.page_templates import BookTemplates

    detector_input = _empty_detector_input()
    assert detector_input.page_index == 0
    assert isinstance(detector_input.templates, BookTemplates)
    assert detector_input.classification.page_class == "unknown"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/regions/test_detector.py -v`
Expected: FAIL with `ImportError: cannot import name 'DetectorInput'`.

If instead it fails constructing `PageMeasurement`, read that dataclass in
`pdomain-pgdp-measure/src/pdomain_pgdp_measure/profile_models.py` and supply whatever its
`__post_init__` requires. Do not weaken the test to a `Mock` — a real object here is what catches a
field rename in the measurement package.

- [ ] **Step 3: Widen the seam**

In `src/pdomain_ocr_labeler_spa/core/regions/detector.py`, replace the `RegionDetector` alias and
`null_region_detector`, and add `DetectorInput`, keeping `DetectedRegion` exactly as it is.

```python
@dataclass(frozen=True)
class DetectorInput:
    """Everything a detector may read about one page of one book.

    The seam started as ``Callable[[Page], ...]`` and that was not enough. A
    detector needs the page's index to find its own classification, and the
    book's fitted templates to know where the text block sits — the templates
    are the book's own measured geometry, which is what a fixed threshold can
    never be. Passing one frozen object rather than five arguments means a
    later detector that needs a sixth signal does not change every call site.
    """

    page: Page
    page_index: int
    measurement: PageMeasurement
    classification: PageClassification
    templates: BookTemplates


RegionDetector = Callable[[DetectorInput], Sequence[DetectedRegion]]
"""Takes one page and the book it belongs to, and returns what it detected."""


def null_region_detector(detector_input: DetectorInput) -> list[DetectedRegion]:
    """The default detector: proposes nothing. Keeps the job runnable with no engine wired."""
    del detector_input  # unused — this is the explicit no-op the seam defaults to
    return []


__all__ = ["DetectedRegion", "DetectorInput", "RegionDetector", "null_region_detector"]
```

Add these imports at the top of the file, beside the existing ones:

```python
from pdomain_pgdp_measure.page_templates import BookTemplates, PageClassification
from pdomain_pgdp_measure.profile_models import PageMeasurement
```

- [ ] **Step 4: Fix the one call site**

`core/jobs/handlers/propose_regions.py` calls `await asyncio.to_thread(detector, page)`. It has no
measurement or templates yet — Task 2 supplies those. Until then it cannot build a real
`DetectorInput`, so **do not fake one**. Instead, in this task only, guard the call:

```python
        # Task 2 supplies the book measurement this detector call needs. Until
        # it lands there is nothing to build a DetectorInput from, so the run
        # proposes nothing — which is exactly what the default detector did
        # before the seam widened. Removing this guard is Task 2's first step.
        detected: Sequence[DetectedRegion] = []
```

Delete the now-unused `detector` local and the `region_detector` context lookup in this task, and
delete the `RegionDetector` and `null_region_detector` imports if nothing else uses them. Leave the
per-page loop, the progress reporting, and the run append exactly as they are: the run still records
what it read, and it still writes zero proposals, which is the behaviour before this task.

Let ruff and basedpyright tell you which imports became unused. Do not guess.

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/unit/core/regions/test_detector.py tests/integration/test_region_proposals_router.py -v`
Expected: PASS. The Task 5 tests that assert an empty proposal journal still pass, because the run
still proposes nothing.

- [ ] **Step 6: Run the gate and commit**

```bash
export PATH="$PWD/.venv-container/bin:$PATH"
uv run ruff check src/ tests/ && uv run ruff format src/ tests/
uv run basedpyright src/pdomain_ocr_labeler_spa --level error
make AI=1 test
git add src/pdomain_ocr_labeler_spa/core/regions/detector.py \
  src/pdomain_ocr_labeler_spa/core/jobs/handlers/propose_regions.py \
  tests/unit/core/regions/test_detector.py
git commit -m "refactor(regions): widen the detector seam to a fitted book"
```

---

### Task 2: Measure the book once, from both jobs

`propose_page_kinds` measures every page, fits the book, and classifies it. `propose_regions` needs
the same three things. Extract that pass into one function both jobs call, then have
`propose_regions` build a `DetectorInput` per page from its output.

**Files:**

- Create: `src/pdomain_ocr_labeler_spa/core/page_measurement.py`
- Modify: `src/pdomain_ocr_labeler_spa/core/jobs/handlers/propose_page_kinds.py`
- Modify: `src/pdomain_ocr_labeler_spa/core/jobs/handlers/propose_regions.py`
- Test: `tests/unit/core/test_page_measurement.py`
- Test: `tests/unit/core/jobs/test_propose_regions_handler.py`

**Interfaces:**

- Consumes: `Project` from `core/models`; `ProfileInputPage` from
  `pdomain_pgdp_measure.profile_input`; `profile_page` from `pdomain_pgdp_measure.profiling`;
  `fit_book_templates`, `classify_pages` from `pdomain_pgdp_measure.page_templates`;
  `DetectorInput` from Task 1.
- Produces: `MeasuredBook` (frozen dataclass with `measurements: tuple[PageMeasurement, ...]`,
  `classifications: tuple[PageClassification, ...]`, `templates: BookTemplates`);
  `async def measure_book(project, *, measure_fn, on_page_measured) -> MeasuredBook`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/core/test_page_measurement.py`:

```python
"""Unit tests for the shared measure-and-fit pass over one book."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from pdomain_pgdp_measure.profile_input import ProfileInputPage
from pdomain_pgdp_measure.profile_models import PageMeasurement


def _fake_measurement(project_id: str, page: ProfileInputPage) -> PageMeasurement:
    del project_id
    return PageMeasurement(
        page_name=page.name,
        source_path=page.source_path or f"book1/{page.name}",
        sha256=None,
        source_frame=None,
        image_mode=None,
        grayscale_threshold=None,
        foreground_pixels=None,
        foreground_bounds=None,
        margins=None,
    )


class _FakeProject:
    project_id = "book1"
    total_pages = 3

    def __init__(self, tmp_path: Path) -> None:
        self.project_root = tmp_path
        self.image_paths = [tmp_path / f"00{n}.png" for n in (1, 2, 3)]


def test_measure_book_measures_every_image_path_and_reports_progress(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.page_measurement import measure_book

    seen: list[tuple[int, int]] = []

    async def on_page_measured(current: int, total: int) -> None:
        seen.append((current, total))

    result = asyncio.run(
        measure_book(
            _FakeProject(tmp_path),
            measure_fn=_fake_measurement,
            on_page_measured=on_page_measured,
        )
    )

    assert len(result.measurements) == 3
    assert [m.page_name for m in result.measurements] == ["001.png", "002.png", "003.png"]
    assert seen == [(1, 3), (2, 3), (3, 3)]


def test_measure_book_returns_one_classification_per_measured_page(tmp_path: Path) -> None:
    """classify_pages preserves input order, so page_index is recovered by position.

    That order-preservation is documented behaviour, not a type-checked contract,
    so the length check is what makes relying on it safe.
    """
    from pdomain_ocr_labeler_spa.core.page_measurement import measure_book

    async def _noop(current: int, total: int) -> None:
        del current, total

    result = asyncio.run(
        measure_book(_FakeProject(tmp_path), measure_fn=_fake_measurement, on_page_measured=_noop)
    )
    assert len(result.classifications) == len(result.measurements)


def test_measure_book_on_a_book_with_no_pages_returns_empty(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.page_measurement import measure_book

    class _EmptyProject:
        project_id = "book1"
        total_pages = 0

        def __init__(self) -> None:
            self.project_root = tmp_path
            self.image_paths: list[Path] = []

    async def _noop(current: int, total: int) -> None:
        del current, total

    result = asyncio.run(
        measure_book(_EmptyProject(), measure_fn=_fake_measurement, on_page_measured=_noop)
    )
    assert result.measurements == ()
    assert result.classifications == ()
    assert result.templates.has_type_page is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/test_page_measurement.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pdomain_ocr_labeler_spa.core.page_measurement'`.

- [ ] **Step 3: Write the shared pass**

Create `src/pdomain_ocr_labeler_spa/core/page_measurement.py`:

```python
"""One measure-and-fit pass over a whole book, shared by both proposal jobs.

``propose_page_kinds`` needs every page measured before it can classify any —
``fit_book_templates`` measures the whole book's first-band geometry before
classifying a single page against it. ``propose_regions`` needs the same three
outputs: each page's measurement, each page's classification, and the book's
fitted templates. Running that pass twice in two files is how the two jobs end
up disagreeing about the same book.

The measurement is not persisted. A region run re-measures rather than reading
a stored result, because the page-kind journal records only ``run_id``,
``model_id``, ``model_version``, ``created_at`` and ``page_count`` — it has no
per-facet staleness machinery, so a stored measurement would need a new record
carrying its own image digest and a rule for what to do when that digest stops
matching. See the design's "The measurement has to reach the run".
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from pdomain_pgdp_measure.page_templates import (
    BookTemplates,
    PageClassification,
    classify_pages,
    fit_book_templates,
)
from pdomain_pgdp_measure.profile_input import ProfileInputPage
from pdomain_pgdp_measure.profile_models import PageMeasurement

if TYPE_CHECKING:
    from .models import Project

log = logging.getLogger(__name__)


class MeasurePageFn(Protocol):
    """The ``profile_page`` shape, as an injection point for tests."""

    def __call__(self, project_id: str, page: ProfileInputPage) -> PageMeasurement: ...


ProgressFn = Callable[[int, int], Awaitable[None]]
"""Called after each page with ``(pages_done, pages_total)``."""


@dataclass(frozen=True)
class MeasuredBook:
    """One book's measured geometry: per page, and fitted across the whole volume."""

    measurements: tuple[PageMeasurement, ...]
    classifications: tuple[PageClassification, ...]
    templates: BookTemplates


async def measure_book(
    project: "Project",
    *,
    measure_fn: MeasurePageFn,
    on_page_measured: ProgressFn,
) -> MeasuredBook:
    """Measure every page of ``project``, fit its templates, and classify it.

    Walks ``project.image_paths`` — the same sequence the progress denominator
    comes from, so the two can never disagree.
    """
    image_paths = list(project.image_paths)
    total = len(image_paths)
    measurements: list[PageMeasurement] = []
    for page_index, image_path in enumerate(image_paths):
        input_page = ProfileInputPage(
            name=image_path.name,
            image_path=image_path,
            source_path=f"{project.project_id}/{image_path.name}",
        )
        # ``profile_page`` decodes the image and scans it with numpy — CPU-bound
        # work that would block the one event loop for the whole book. Offload it
        # the way every other image-touching handler does, so the confirm route
        # and the job's own progress stream keep being served.
        measurements.append(await asyncio.to_thread(measure_fn, project.project_id, input_page))
        await on_page_measured(page_index + 1, total)

    templates = fit_book_templates(measurements)
    classifications = classify_pages(measurements, templates)
    # classify_pages preserves input order, so page_index is recovered by
    # position. That order-preservation is documented behaviour, not a
    # type-checked contract, so this explicit check — written out rather than
    # asserted, to survive -O — is what makes relying on it safe.
    if len(classifications) != len(measurements):
        raise RuntimeError(
            "measure_book: classify_pages returned "
            f"{len(classifications)} classification(s) for {len(measurements)} measured "
            "page(s) — page_index recovery by position is no longer safe"
        )
    return MeasuredBook(tuple(measurements), tuple(classifications), templates)


__all__ = ["MeasuredBook", "MeasurePageFn", "ProgressFn", "measure_book"]
```

- [ ] **Step 4: Run the new test**

Run: `uv run pytest tests/unit/core/test_page_measurement.py -v`
Expected: PASS, all three tests.

- [ ] **Step 5: Have `propose_page_kinds` use it**

In `core/jobs/handlers/propose_page_kinds.py`, replace the inline measurement loop, the
`fit_book_templates` call, the `classify_pages` call, and the length check with one `measure_book`
call. Keep everything else: the context wiring, the book-pin guard, the `_to_kind_and_confidence`
mapping, the journal append, and the notification.

The progress callback preserves the existing message wording exactly:

```python
    async def _report(current: int, total_pages: int) -> None:
        await runner.update_progress(
            job.job_id,
            current=current,
            total=total_pages,
            message=f"Measured page {current}/{total_pages}",
        )

    measured = await measure_book(project, measure_fn=measure_fn, on_page_measured=_report)
    classifications = measured.classifications
```

Delete `_MeasurePageFn` from this file and import `MeasurePageFn` from `core.page_measurement`
instead — one protocol, one definition. Keep the `ctx.get("propose_page_kinds_measure_fn")`
injection point exactly as it is; the existing handler tests depend on it.

- [ ] **Step 6: Run the page-kind tests**

Run: `uv run pytest tests/unit/core/jobs/test_propose_page_kinds_handler.py -v`
Expected: PASS with no test changes. If a test fails, the extraction changed behaviour — find out
which and fix the extraction, not the test.

- [ ] **Step 7: Write the failing `propose_regions` test**

Create `tests/unit/core/jobs/test_propose_regions_handler.py`:

```python
"""Unit tests for the propose_regions handler's measurement pass."""

from __future__ import annotations

from typing import Any


def test_the_handler_hands_the_detector_one_input_per_eligible_page(
    proposal_run_ready: Any,
) -> None:
    """The detector sees the page, its index, its classification, and the book.

    ``proposal_run_ready`` is defined in this file's sibling conftest and yields
    ``(runner, job, project_state)`` with two pages loaded, both carrying a
    confirmed page kind, and a stub measure function wired into
    ``runner.context``.
    """
    import asyncio

    from pdomain_ocr_labeler_spa.core.jobs.handlers.propose_regions import handle_propose_regions
    from pdomain_ocr_labeler_spa.core.regions.detector import DetectorInput

    runner, job, _project_state = proposal_run_ready
    seen: list[DetectorInput] = []

    def _recording_detector(detector_input: DetectorInput) -> list[Any]:
        seen.append(detector_input)
        return []

    runner.context["region_detector"] = _recording_detector
    asyncio.run(handle_propose_regions(runner, job))

    assert [d.page_index for d in seen] == [0, 1]
    assert all(d.classification is not None for d in seen)
    assert all(d.templates is not None for d in seen)
    assert all(d.measurement.page_name for d in seen)


def test_a_detected_region_becomes_a_proposal_in_the_journal(proposal_run_ready: Any) -> None:
    import asyncio

    from pdomain_book_contracts.annotation import RegionRole

    from pdomain_ocr_labeler_spa.core.jobs.handlers.propose_regions import handle_propose_regions
    from pdomain_ocr_labeler_spa.core.regions.detector import DetectedRegion, DetectorInput
    from pdomain_ocr_labeler_spa.core.regions.proposal_log import RegionProposalLog

    runner, job, project_state = proposal_run_ready

    def _one_region_detector(detector_input: DetectorInput) -> list[DetectedRegion]:
        del detector_input
        return [
            DetectedRegion(
                role=RegionRole.PAGE_HEADER,
                box=(10, 20, 190, 40),
                confidence=0.75,
                evidence={"signal": "test"},
            )
        ]

    runner.context["region_detector"] = _one_region_detector
    asyncio.run(handle_propose_regions(runner, job))

    project = project_state.loaded_project
    assert project is not None
    log = RegionProposalLog(project.project_root)
    runs = log.runs()
    assert len(runs) == 1
    # RegionProposalLog exposes proposals_for_page, not proposals_for_run —
    # the run-scoped accessor is PageKindProposalLog's, a different class.
    proposals = [p for idx in (0, 1) for p in log.proposals_for_page(idx, run_id=runs[0].run_id)]
    assert len(proposals) == 2
    assert {p.page_index for p in proposals} == {0, 1}
    assert all(p.role is RegionRole.PAGE_HEADER for p in proposals)
    assert all(p.confidence == 0.75 for p in proposals)
```

Write the `proposal_run_ready` fixture in `tests/unit/core/jobs/conftest.py`, creating it if that
file does not exist. It must build a `ProjectState` with two loaded pages whose `page_record.payload`
is a real `Page`, mark both kinds confirmed through `PageKindReviewedStore.mark_reviewed`, construct
a `JobRunner` with `project_state` in its context, put a stub measure function in
`runner.context["propose_regions_measure_fn"]` returning a valid `PageMeasurement` per page, and
register the `Job` in `runner._jobs`. Copy the `Job` construction and the `runner._jobs[job.job_id]`
direct enqueue from the existing tests at the bottom of
`tests/integration/test_region_proposals_router.py` — they are the working precedent for this.

- [ ] **Step 8: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/jobs/test_propose_regions_handler.py -v`
Expected: FAIL. The handler proposes nothing because Task 1 Step 4 hard-coded `detected = []`, so
`seen` is empty and the journal holds no proposals.

- [ ] **Step 9: Wire the measurement into `propose_regions`**

In `core/jobs/handlers/propose_regions.py`, after the eligibility pass has produced
`eligible_indices` and before the `ProposalRun` is built:

```python
    # The detector needs the book, not just one page: where the head band
    # belongs and how wide the text block is are book-level facts. Measure the
    # whole volume the way propose_page_kinds does, through the same shared pass.
    measure_fn: MeasurePageFn = ctx.get("propose_regions_measure_fn") or profile_page

    async def _report_measured(current: int, total_pages: int) -> None:
        await runner.update_progress(
            job.job_id,
            current=current,
            total=total_pages,
            message=f"Measuring page {current}/{total_pages}",
        )

    measured = await measure_book(project, measure_fn=measure_fn, on_page_measured=_report_measured)
```

Return `ctx` from `_get_required_context` alongside `project_state` and `page_store`, or read
`runner.context` again — either is fine, say which you chose.

Replace the Task 1 guard in the per-page loop with a real `DetectorInput`:

```python
        if page is not None and idx < len(measured.measurements):
            detector_input = DetectorInput(
                page=page,
                page_index=idx,
                measurement=measured.measurements[idx],
                classification=measured.classifications[idx],
                templates=measured.templates,
            )
            # CPU-bound in the general case — slice 4's furniture detector walks
            # every word box on the page. Offloaded for the same reason the
            # facet-digest snapshot is.
            detected = await asyncio.to_thread(detector, detector_input)
```

**The index join is the thing to get right.** `measured.measurements` is indexed by position in
`project.image_paths`, and `idx` is a `ProjectState.page_states` key. They agree today because both
count pages of the same book from zero. The `idx < len(...)` guard above makes a disagreement
skip the page rather than raise `IndexError` or, worse, attribute page 7's measurement to page 3.
Log a warning when it skips, naming both numbers.

Restore the `detector` lookup and the `RegionDetector` / `null_region_detector` imports that Task 1
removed.

- [ ] **Step 10: Run the tests**

Run the handler tests for both jobs and the proposals-router tests:

```bash
uv run pytest tests/unit/core/jobs/test_propose_regions_handler.py \
  tests/unit/core/jobs/test_propose_page_kinds_handler.py \
  tests/integration/test_region_proposals_router.py -v
```
Expected: PASS.

- [ ] **Step 11: Run the gate and commit**

```bash
export PATH="$PWD/.venv-container/bin:$PATH"
uv run ruff check src/ tests/ && uv run ruff format src/ tests/
uv run basedpyright src/pdomain_ocr_labeler_spa --level error
make AI=1 test
git add src/pdomain_ocr_labeler_spa/core/page_measurement.py \
  src/pdomain_ocr_labeler_spa/core/jobs/handlers/propose_page_kinds.py \
  src/pdomain_ocr_labeler_spa/core/jobs/handlers/propose_regions.py \
  tests/unit/core/test_page_measurement.py \
  tests/unit/core/jobs/test_propose_regions_handler.py \
  tests/unit/core/jobs/conftest.py
git commit -m "feat(regions): measure the book from the propose_regions job"
```

---

### Task 3: The furniture detector

Turn each page's top furniture bands into `page header` and `page number` proposals. This is the
only task that knows what a running head looks like.

**Files:**

- Create: `src/pdomain_ocr_labeler_spa/core/regions/furniture.py`
- Test: `tests/unit/core/regions/test_furniture.py`

**Interfaces:**

- Consumes: `DetectorInput`, `DetectedRegion` from `core/regions/detector`; `RegionRole` from
  `pdomain_book_contracts.annotation`; `Word` from `pdomain_book_tools.ocr.word`.
- Produces: `furniture_region_detector(detector_input: DetectorInput) -> list[DetectedRegion]`;
  `FOLIO_GAP_SHARE_OF_TEXT_WIDTH: float`.

**What the detector does, in order:**

1. Read `detector_input.classification.furniture_band_ordinals`. Empty means propose nothing. It is
   empty for an unclassified page and for a chapter opening, and that is the classifier refusing to
   guess. Honour the refusal.
2. Read `detector_input.measurement.ink_bands`. Take the bands whose ordinals are named. An ordinal
   outside the band tuple is a measurement the classifier and the profile disagree about; skip the
   page and log it.
3. Collect the page's words whose vertical midpoint falls inside the union of those bands' y ranges.
4. Sort them by left edge and split into clusters wherever the horizontal gap to the next word
   exceeds `FOLIO_GAP_SHARE_OF_TEXT_WIDTH` of the book's fitted text width.
5. Emit one `DetectedRegion` per cluster, boxed by the union of its words' boxes.

**Role and confidence rules:**

- A cluster whose text is entirely digits, roman numerals, or both proposes `PAGE_NUMBER`.
- Every other cluster proposes `PAGE_HEADER`. A running head is the more common of the two and a
  reviewer corrects a wrong one in a single click.
- Confidence starts at the page's `classification.confidence`, or `0.5` when the classifier
  recorded none, and is multiplied by `0.8` when the page produced a single cluster that is not a
  folio. A page with one wide cluster could be a running head, or it could be the top line of body
  text on a page whose head band was misplaced.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/core/regions/test_furniture.py`:

```python
"""Unit tests for the top-furniture region detector."""

from __future__ import annotations

from typing import Any

from pdomain_book_contracts.annotation import RegionRole
from pdomain_book_tools.ocr.page import Page
from pdomain_pgdp_measure.page_templates import (
    BookTemplates,
    PageClassification,
    PageTemplate,
)
from pdomain_pgdp_measure.profile_models import InkBand, PageMeasurement

_PAGE_WIDTH = 1000
_PAGE_HEIGHT = 1600


# Pages are built from dicts through ``Page.from_dict``, the way
# tests/integration/conftest.py does. ``Word.__init__`` takes ``text``
# positionally and has no ``ocr_text`` parameter, and ``Block.__init__`` takes
# ``items`` first — the dict form sidesteps both and is what the repo already
# uses everywhere.
def _bbox(left: int, top: int, right: int, bottom: int, *, normalized: bool = False) -> dict[str, object]:
    return {
        "top_left": {"x": left, "y": top},
        "bottom_right": {"x": right, "y": bottom},
        "is_normalized": normalized,
    }


def _word(
    text: str, left: int, top: int, right: int, bottom: int, *, normalized: bool = False
) -> dict[str, object]:
    return {
        "type": "Word",
        "text": text,
        "ground_truth_text": text,
        "bounding_box": _bbox(left, top, right, bottom, normalized=normalized),
    }


def _page(words: list[dict[str, object]], *, normalized: bool = False) -> Page:
    return Page.from_dict(
        {
            "width": _PAGE_WIDTH,
            "height": _PAGE_HEIGHT,
            "page_index": 0,
            "bounding_box": _bbox(0, 0, _PAGE_WIDTH, _PAGE_HEIGHT, normalized=normalized),
            "items": [
                {
                    "type": "Block",
                    "child_type": "WORDS",
                    "block_category": "LINE",
                    "items": words,
                    "bounding_box": _bbox(0, 0, _PAGE_WIDTH, _PAGE_HEIGHT, normalized=normalized),
                }
            ],
        }
    )


def _templates() -> BookTemplates:
    template = PageTemplate(
        page_class="normal_recto",
        first_band_top_px=100,
        first_band_spread_px=6,
        text_left_px=100,
        text_right_px=900,
        band_count=30,
        page_count=200,
        page_share=0.5,
    )
    return BookTemplates(100.0, 4.0, 16.0, (template,), 0.9)


def _measurement(bands: tuple[InkBand, ...]) -> PageMeasurement:
    return PageMeasurement(
        page_name="001.png",
        source_path="book1/001.png",
        sha256=None,
        source_frame=None,
        image_mode=None,
        grayscale_threshold=None,
        foreground_pixels=None,
        foreground_bounds=None,
        margins=None,
        ink_bands=bands,
        page_class="normal_recto",
    )


def _input(
    words: list[dict[str, object]],
    *,
    bands: tuple[InkBand, ...] = (InkBand(100, 130),),
    ordinals: tuple[int, ...] = (0,),
    page_class: str = "normal_recto",
    confidence: float | None = 0.9,
    normalized: bool = False,
) -> Any:
    from pdomain_ocr_labeler_spa.core.regions.detector import DetectorInput

    return DetectorInput(
        page=_page(words, normalized=normalized),
        page_index=0,
        measurement=_measurement(bands),
        classification=PageClassification("001.png", page_class, 2, ordinals, confidence),
        templates=_templates(),
    )


def test_a_running_head_and_a_folio_become_two_regions() -> None:
    """Hierarchy rule 3: they are always separate blocks, same physical line or not."""
    from pdomain_ocr_labeler_spa.core.regions.furniture import furniture_region_detector

    words = [
        _word("THE", 100, 105, 170, 125),
        _word("VOYAGE", 180, 105, 320, 125),
        _word("17", 870, 105, 900, 125),
    ]
    detected = furniture_region_detector(_input(words))

    assert len(detected) == 2
    head, folio = detected
    assert head.role is RegionRole.PAGE_HEADER
    assert head.box == (100, 105, 320, 125)
    assert folio.role is RegionRole.PAGE_NUMBER
    assert folio.box == (870, 105, 900, 125)


def test_a_roman_numeral_folio_is_a_page_number() -> None:
    from pdomain_ocr_labeler_spa.core.regions.furniture import furniture_region_detector

    words = [
        _word("PREFACE", 100, 105, 260, 125),
        _word("xvii", 860, 105, 900, 125),
    ]
    detected = furniture_region_detector(_input(words))
    assert [d.role for d in detected] == [RegionRole.PAGE_HEADER, RegionRole.PAGE_NUMBER]


def test_a_page_with_no_furniture_bands_proposes_nothing() -> None:
    """An unclassified page and a chapter opening both record no furniture bands."""
    from pdomain_ocr_labeler_spa.core.regions.furniture import furniture_region_detector

    words = [_word("THE", 100, 105, 170, 125)]
    assert furniture_region_detector(_input(words, ordinals=())) == []


def test_words_below_the_furniture_band_are_not_furniture() -> None:
    from pdomain_ocr_labeler_spa.core.regions.furniture import furniture_region_detector

    words = [
        _word("THE", 100, 105, 170, 125),
        _word("body", 100, 400, 190, 420),
    ]
    detected = furniture_region_detector(_input(words))
    assert len(detected) == 1
    assert detected[0].box == (100, 105, 170, 125)


def test_a_lone_wide_cluster_is_a_header_at_reduced_confidence() -> None:
    from pdomain_ocr_labeler_spa.core.regions.furniture import furniture_region_detector

    words = [_word("THE", 100, 105, 170, 125), _word("VOYAGE", 180, 105, 320, 125)]
    detected = furniture_region_detector(_input(words, confidence=0.9))
    assert len(detected) == 1
    assert detected[0].role is RegionRole.PAGE_HEADER
    assert detected[0].confidence == 0.9 * 0.8


def test_a_lone_folio_keeps_full_confidence() -> None:
    from pdomain_ocr_labeler_spa.core.regions.furniture import furniture_region_detector

    detected = furniture_region_detector(_input([_word("17", 870, 105, 900, 125)], confidence=0.9))
    assert len(detected) == 1
    assert detected[0].role is RegionRole.PAGE_NUMBER
    assert detected[0].confidence == 0.9


def test_a_classification_with_no_confidence_falls_back_to_one_half() -> None:
    from pdomain_ocr_labeler_spa.core.regions.furniture import furniture_region_detector

    detected = furniture_region_detector(_input([_word("17", 870, 105, 900, 125)], confidence=None))
    assert detected[0].confidence == 0.5


def test_an_ordinal_past_the_end_of_the_bands_proposes_nothing() -> None:
    """The classifier and the profile disagree; skip rather than guess."""
    from pdomain_ocr_labeler_spa.core.regions.furniture import furniture_region_detector

    words = [_word("THE", 100, 105, 170, 125)]
    assert furniture_region_detector(_input(words, ordinals=(0, 5))) == []


def test_the_evidence_names_the_band_and_the_cluster_width() -> None:
    from pdomain_ocr_labeler_spa.core.regions.furniture import furniture_region_detector

    words = [_word("THE", 100, 105, 170, 125), _word("17", 870, 105, 900, 125)]
    detected = furniture_region_detector(_input(words))
    assert detected[0].evidence["band_ordinals"] == [0]
    assert detected[0].evidence["cluster_width_px"] == 70
    assert detected[0].evidence["text_width_px"] == 800
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/regions/test_furniture.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named '...core.regions.furniture'`.

If instead it fails building the page or an `InkBand`, read those constructors and supply what they
require. Adjust the helper, not the assertions. The helper deliberately builds the page from a dict
through `Page.from_dict` rather than calling `Word` and `Block` directly, because `Word.__init__`
takes `text` as its first positional argument and has no `ocr_text` parameter, and `Block.__init__`
takes `items` first. The dict form is what every other test in this repo uses.

- [ ] **Step 3: Write the detector**

Create `src/pdomain_ocr_labeler_spa/core/regions/furniture.py`:

```python
"""Propose page furniture — the running head and the folio — from band geometry.

Spec authority: pdomain-ocr-synth's
docs/specs/2026-09-17-geometry-region-proposals-design.md, "Start with page
furniture" and "A furniture band becomes one or two regions, not one".

``furniture_band_ordinals`` names every ink band from the top of the page down
to and including the running-head band. The classifier can say this without
ambiguity because nothing is printed above the head. It is empty for a chapter
opening and for a page the classifier declined to classify, and empty means
propose nothing — never "guess from the top band".

The band gives the vertical extent. An ``InkBand`` is a row projection and
carries no horizontal extent at all, so where the ink sits across the page comes
from the page's own word boxes. A running head and a folio share one band and
are always separate regions (region-vocabulary hierarchy rule 3), so the words
in a band are split on a horizontal gap.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass

from pdomain_book_contracts.annotation import RegionRole
from pdomain_book_tools.ocr.block import Block
from pdomain_book_tools.ocr.page import Page
from pdomain_book_tools.ocr.word import Word

from .detector import DetectedRegion, DetectorInput

log = logging.getLogger(__name__)

FOLIO_GAP_SHARE_OF_TEXT_WIDTH = 0.10
"""Split a band's words into separate regions at a gap this wide.

Measured against the book's own fitted text width, not a pixel constant — the
same principle the word-gap finding established, that a threshold shared across
books is wrong in every one of them. A running head and a folio are typically
separated by 30 to 70 percent of the text width, while the spaces inside a head
run 1 to 3 percent, so 10 percent sits in a wide empty gap between the two.
This is a starting value and the first review pass over real proposals should
check it.
"""

_LONE_HEADER_CONFIDENCE_FACTOR = 0.8
"""A single wide cluster could be a head, or body text under a misplaced band."""

_NO_CLASSIFIER_CONFIDENCE = 0.5
"""Used when the classifier recorded no confidence for the page."""

_FOLIO_PATTERN = re.compile(r"^[0-9ivxlcdmIVXLCDM]+$")
"""Digits, roman numerals, or both. Anything else reads as a running head."""


@dataclass(frozen=True)
class _Cluster:
    """One horizontal run of words inside the furniture bands."""

    words: list[Word]

    @property
    def box(self) -> tuple[int, int, int, int]:
        boxes = [w.bounding_box for w in self.words]
        return (
            int(min(b.minX for b in boxes)),
            int(min(b.minY for b in boxes)),
            int(max(b.maxX for b in boxes)),
            int(max(b.maxY for b in boxes)),
        )

    @property
    def text(self) -> str:
        return " ".join(w.ground_truth_text or w.ocr_text or "" for w in self.words).strip()

    @property
    def is_folio(self) -> bool:
        stripped = self.text.replace(" ", "")
        return bool(stripped) and bool(_FOLIO_PATTERN.match(stripped))


def _page_words(page: Page) -> list[Word]:
    """Every word on the page, at any nesting depth.

    Mirrors ``block_adapter._walk_blocks``, which walks the same tree for
    blocks. Duplicated rather than generalized: one walker that yields both
    would make every call site filter, and the two callers want different
    things.
    """
    words: list[Word] = []

    def walk(items: Sequence[Word | Block]) -> None:
        for item in items:
            if isinstance(item, Word):
                words.append(item)
            else:
                walk(item.items)

    walk(page.items)
    return words


def _text_width_px(detector_input: DetectorInput) -> int | None:
    """The book's fitted text width, or ``None`` when it has no templates."""
    templates = detector_input.templates.templates
    if not templates:
        return None
    widths = [
        t.text_right_px - t.text_left_px for t in templates if t.text_right_px > t.text_left_px
    ]
    return max(widths) if widths else None


def _cluster(words: list[Word], gap_px: float) -> list[_Cluster]:
    """Split words sorted by left edge wherever the gap to the next exceeds ``gap_px``."""
    if not words:
        return []
    ordered = sorted(words, key=lambda w: w.bounding_box.minX)
    clusters: list[list[Word]] = [[ordered[0]]]
    for word in ordered[1:]:
        previous_right = max(w.bounding_box.maxX for w in clusters[-1])
        if word.bounding_box.minX - previous_right > gap_px:
            clusters.append([word])
        else:
            clusters[-1].append(word)
    return [_Cluster(group) for group in clusters]


def furniture_region_detector(detector_input: DetectorInput) -> list[DetectedRegion]:
    """Propose one region per horizontal cluster inside the page's furniture bands."""
    ordinals = detector_input.classification.furniture_band_ordinals
    if not ordinals:
        return []

    bands = detector_input.measurement.ink_bands or ()
    if any(ordinal >= len(bands) for ordinal in ordinals):
        log.warning(
            "furniture_region_detector: page=%s names band ordinals %s but the profile "
            "recorded %d band(s) — skipping the page",
            detector_input.classification.page_name,
            list(ordinals),
            len(bands),
        )
        return []

    text_width = _text_width_px(detector_input)
    if text_width is None:
        return []

    top = min(bands[o].y_start for o in ordinals)
    bottom = max(bands[o].y_end for o in ordinals)
    in_band = [
        word
        for word in _page_words(detector_input.page)
        if word.bounding_box.has_usable_coordinates
        and top <= (word.bounding_box.minY + word.bounding_box.maxY) / 2 <= bottom
    ]
    if not in_band:
        return []

    clusters = _cluster(in_band, text_width * FOLIO_GAP_SHARE_OF_TEXT_WIDTH)
    base = detector_input.classification.confidence
    if base is None:
        base = _NO_CLASSIFIER_CONFIDENCE

    detected: list[DetectedRegion] = []
    for cluster in clusters:
        left, cluster_top, right, cluster_bottom = cluster.box
        is_folio = cluster.is_folio
        confidence = base
        if len(clusters) == 1 and not is_folio:
            confidence = base * _LONE_HEADER_CONFIDENCE_FACTOR
        detected.append(
            DetectedRegion(
                role=RegionRole.PAGE_NUMBER if is_folio else RegionRole.PAGE_HEADER,
                box=(left, cluster_top, right, cluster_bottom),
                confidence=round(min(1.0, max(0.0, confidence)), 6),
                evidence={
                    "band_ordinals": list(ordinals),
                    "band_y_range": [top, bottom],
                    "cluster_width_px": right - left,
                    "cluster_count": len(clusters),
                    "text_width_px": text_width,
                    "gap_threshold_px": round(text_width * FOLIO_GAP_SHARE_OF_TEXT_WIDTH, 2),
                    "page_class": detector_input.classification.page_class,
                },
            )
        )
    return detected


__all__ = ["FOLIO_GAP_SHARE_OF_TEXT_WIDTH", "furniture_region_detector"]
```

- [ ] **Step 4: Handle the normalized-coordinate case**

The code above compares `word.bounding_box.minY` against a band's `y_start`, which is a source-frame
pixel. On a page whose word boxes are normalized to 0 to 1, that comparison is meaningless and the
detector would silently propose nothing on every page.

Add this guard at the top of `furniture_region_detector`, after the `ordinals` check:

```python
    try:
        if detector_input.page.is_content_normalized:
            log.warning(
                "furniture_region_detector: page=%s has normalized word boxes; ink bands "
                "are source-frame pixels, so this page is skipped",
                detector_input.classification.page_name,
            )
            return []
    except ValueError:
        # Page.is_content_normalized raises on a page that mixes normalized and
        # pixel boxes. A detector cannot compare either convention against a
        # band, so the page is skipped rather than half-measured.
        log.warning(
            "furniture_region_detector: page=%s mixes normalized and pixel word boxes; skipping",
            detector_input.classification.page_name,
        )
        return []
```

Add a test for both branches to `tests/unit/core/regions/test_furniture.py`:

```python
def test_a_page_with_normalized_word_boxes_is_skipped() -> None:
    """Ink bands are source-frame pixels; a 0-to-1 box cannot be compared against one."""
    from pdomain_ocr_labeler_spa.core.regions.furniture import furniture_region_detector

    words = [_word("THE", 0, 0, 0, 0, normalized=True)]
    assert furniture_region_detector(_input(words, normalized=True)) == []
```

The `_bbox` helper stamps `is_normalized` explicitly rather than letting it be inferred, the same
way `tests/integration/conftest.py:_tb_bbox` does.

`Page.is_content_normalized` is verified: it walks every word with a bounding box, returns the
shared `is_normalized` flag when they all agree, returns `False` when no word has a box, and raises
`ValueError` when the page mixes the two conventions. So the guard's two branches are both real. Add
a test for the mixed case as well:

```python
def test_a_page_mixing_normalized_and_pixel_boxes_is_skipped() -> None:
    """Page.is_content_normalized raises on a mixed page; a detector cannot pick a side."""
    from pdomain_ocr_labeler_spa.core.regions.furniture import furniture_region_detector

    words = [
        _word("THE", 100, 105, 170, 125),
        _word("17", 0, 0, 0, 0, normalized=True),
    ]
    assert furniture_region_detector(_input(words)) == []
```

**It iterates `self.lines`, so a word outside a `LINE`-category block is invisible to it.**
`_page_words` walks the whole item tree and is not limited that way, so the page-level guard alone
would let a stray normalized word reach the band comparison. Close that by filtering per word too.
Change the in-band filter in `furniture_region_detector` to:

```python
    in_band = [
        word
        for word in _page_words(detector_input.page)
        if word.bounding_box.has_usable_coordinates
        # The page-level guard above reads Page.is_content_normalized, which
        # only walks words inside LINE blocks. _page_words walks the whole
        # tree, so a normalized box on a word outside any line would otherwise
        # be compared against a source-frame band y range.
        and not word.bounding_box.is_normalized
        and top <= (word.bounding_box.minY + word.bounding_box.maxY) / 2 <= bottom
    ]
```

The test helper builds one `LINE` block, so both test words are seen by the page-level guard as
well.

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/unit/core/regions/test_furniture.py -v`
Expected: PASS, all ten tests.

- [ ] **Step 6: Run the gate and commit**

```bash
export PATH="$PWD/.venv-container/bin:$PATH"
uv run ruff check src/ tests/ && uv run ruff format src/ tests/
uv run basedpyright src/pdomain_ocr_labeler_spa --level error
make AI=1 test
git add src/pdomain_ocr_labeler_spa/core/regions/furniture.py \
  tests/unit/core/regions/test_furniture.py
git commit -m "feat(regions): propose page furniture from band geometry"
```

---

### Task 4: Wire the detector in, and prove the whole chain

Nothing sets `JobRunner.context["region_detector"]`, so the furniture detector would never run.
Wire it in `bootstrap.py`, then test the whole chain through the routes: propose page kinds, confirm
one, propose regions, list the proposals.

**Files:**

- Modify: `src/pdomain_ocr_labeler_spa/bootstrap.py`
- Test: `tests/integration/test_region_proposal_run_end_to_end.py`

**Interfaces:**

- Consumes: `furniture_region_detector` from `core/regions/furniture`.
- Produces: nothing new. `runner.context["region_detector"]` is set at build time.

- [ ] **Step 1: Write the failing end-to-end test**

Create `tests/integration/test_region_proposal_run_end_to_end.py`:

```python
"""The whole chain: page kinds proposed, one confirmed, regions proposed, proposals listed.

Nothing else exercises the page-kind job and the region job together, and they
are ordered: a page whose kind was never proposed or confirmed gets no region
proposals. This is the test that fails if that ordering breaks.
"""

from __future__ import annotations

from typing import Any


def test_the_default_detector_is_the_furniture_detector(toolbar_loaded: Any) -> None:
    from pdomain_ocr_labeler_spa.core.regions.furniture import furniture_region_detector

    client, _project_state, _page = toolbar_loaded
    runner = client.app.state.job_runner
    assert runner.context["region_detector"] is furniture_region_detector


def test_a_confirmed_page_kind_lets_a_region_run_reach_that_page(toolbar_loaded: Any) -> None:
    """The ordering the design depends on, exercised through the real routes."""
    import asyncio
    from datetime import UTC, datetime

    from pdomain_ocr_labeler_spa.core.jobs.handlers.propose_regions import handle_propose_regions
    from pdomain_ocr_labeler_spa.core.jobs.runner import Job, JobStatus
    from pdomain_ocr_labeler_spa.core.page_kind.reviewed_store import PageKindReviewedStore
    from pdomain_ocr_labeler_spa.core.regions.proposal_log import RegionProposalLog

    client, project_state, _page = toolbar_loaded
    runner = client.app.state.job_runner
    project = project_state.loaded_project
    assert project is not None

    PageKindReviewedStore(project.project_root).mark_reviewed(0, datetime.now(UTC).isoformat())

    job = Job(
        job_id="e2e-job",
        job_type="propose_regions",
        status=JobStatus.RUNNING,
        project_id=project.project_id,
        payload={"project_id": project.project_id},
        created_at=datetime.now(UTC),
    )
    runner._jobs[job.job_id] = job
    asyncio.run(handle_propose_regions(runner, job))

    runs = RegionProposalLog(project.project_root).runs()
    assert len(runs) == 1
    assert 0 in runs[0].page_facet_digests


def test_listing_proposals_returns_what_the_run_wrote(toolbar_loaded: Any) -> None:
    import asyncio
    from datetime import UTC, datetime

    from pdomain_book_contracts.annotation import RegionRole

    from pdomain_ocr_labeler_spa.core.jobs.handlers.propose_regions import handle_propose_regions
    from pdomain_ocr_labeler_spa.core.jobs.runner import Job, JobStatus
    from pdomain_ocr_labeler_spa.core.page_kind.reviewed_store import PageKindReviewedStore
    from pdomain_ocr_labeler_spa.core.regions.detector import DetectedRegion, DetectorInput

    client, project_state, _page = toolbar_loaded
    runner = client.app.state.job_runner
    project = project_state.loaded_project
    assert project is not None
    PageKindReviewedStore(project.project_root).mark_reviewed(0, datetime.now(UTC).isoformat())

    def _one_header(detector_input: DetectorInput) -> list[DetectedRegion]:
        del detector_input
        return [
            DetectedRegion(
                role=RegionRole.PAGE_HEADER,
                box=(10, 5, 90, 20),
                confidence=0.7,
                evidence={"signal": "end-to-end"},
            )
        ]

    runner.context["region_detector"] = _one_header
    job = Job(
        job_id="e2e-job-2",
        job_type="propose_regions",
        status=JobStatus.RUNNING,
        project_id=project.project_id,
        payload={"project_id": project.project_id},
        created_at=datetime.now(UTC),
    )
    runner._jobs[job.job_id] = job
    asyncio.run(handle_propose_regions(runner, job))

    response = client.get("/api/projects/book1/pages/0/regions/proposals")
    assert response.status_code == 200, response.text
    proposals = response.json()["proposals"]
    assert len(proposals) == 1
    assert proposals[0]["role"] == "page header"
    assert proposals[0]["confidence"] == 0.7
    assert proposals[0]["disposition"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_region_proposal_run_end_to_end.py -v`
Expected: the first test FAILS with `KeyError: 'region_detector'`.

The other two should pass once the detector is wired. The `toolbar_loaded` fixture writes a six-byte
fake PNG, and `profile_page` on that file **returns rather than raises**: a `PageMeasurement` with
`page_class="unknown"`, `ink_bands=None`, and a diagnostic of `image_decode_failed`. I ran it to
check. So the measurement pass completes, the furniture detector sees no bands and proposes nothing,
and the run is still recorded — which is exactly what the second test asserts. The third test injects
its own detector because the fixture's page has no real furniture to find.

- [ ] **Step 3: Wire the detector in `bootstrap.py`**

Find where `runner.context` is populated with `project_state` and `notification_queue`, and add:

```python
    # The region proposal engine. Slice 4's furniture detector is the default
    # rather than ``null_region_detector``, because a seam nothing wires is a
    # seam that never runs. A test overrides this key the same way the
    # page-kind measure function is overridden.
    runner.context["region_detector"] = furniture_region_detector
```

Import it at the top of `bootstrap.py`:

```python
from .core.regions.furniture import furniture_region_detector
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/integration/test_region_proposal_run_end_to_end.py -v`
Expected: PASS, all three.

- [ ] **Step 5: Run the gate and commit**

```bash
export PATH="$PWD/.venv-container/bin:$PATH"
uv run ruff check src/ tests/ && uv run ruff format src/ tests/
uv run basedpyright src/pdomain_ocr_labeler_spa --level error
make openapi-export   # expect no diff; report it if there is one
make AI=1 test
git add src/pdomain_ocr_labeler_spa/bootstrap.py \
  tests/integration/test_region_proposal_run_end_to_end.py
git commit -m "feat(regions): run the furniture detector by default"
```

---

## What this plan does not do

- **No bottom-of-page furniture.** `furniture_band_ordinals` names top bands only, because the
  classifier derives it from the running-head band and nothing is printed above that. A page footer,
  a catchword, a signature mark, and a press figure need the mirror of the same logic in
  `pdomain-pgdp-measure`, which is a change in a different repository.
- **No model.** Every role geometry cannot separate waits for slice 6.
- **No region review surface.** Slice 3 builds that. Until it lands, a person reads proposals
  through `GET /{project_id}/pages/{page_index}/regions/proposals` and accepts one through
  `POST .../regions/proposals/{proposal_id}/accept`.
- **No verified page lease.** Both proposal jobs read `project.image_paths` directly, which bypasses
  the manifest hash pin on a book-labeling project. That is tracked separately and is being fixed on
  its own branch; if it has landed before this plan runs, `measure_book` is the one place that needs
  to change.
- **No persisted measurement.** A region run re-measures. The design says why, and says what a
  persisted record would have to carry if measurement time ever becomes the bottleneck.

## Related

- [Geometry region proposals design](../specs/2026-09-17-geometry-region-proposals-design.md) — the
  design this carries out.
- [Region routes and proposal run](2026-09-08-region-routes-and-proposal-run.md) — Task 5 built the
  seam this plan widens.
- [Region vocabulary](../specs/2026-09-07-region-vocabulary-design.md) — hierarchy rule 3, why a
  running head and a folio are two regions.
- [X-height spread does not find chapter openings](../research/2026-09-17-x-height-spread-does-not-find-chapter-openings.md)
  — why no proposal in this plan is gated on x-height spread.
- [Labeling track roadmap](2026-09-07-labeling-track-roadmap.md) — where slice 4 sits.
